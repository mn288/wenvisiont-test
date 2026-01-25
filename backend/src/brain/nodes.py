import uuid
from datetime import datetime

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from brain.logger import LogHandler
from brain.registry import AgentRegistry
from core.database import pool
from crew.agents import llm
from models.state import AgentResult, AgentTask, GraphState
from services.crew import CrewService
from services.infrastructure import InfrastructureService
from services.orchestrator import OrchestratorService
from services.skill_service import skill_service
from utils.pii import mask_pii

# Initialize Services
orchestrator_service = OrchestratorService()
crew_service = CrewService()
infrastructure_service = InfrastructureService()


async def preprocess_node(state: GraphState, config: RunnableConfig) -> dict:
    """Validate input and initialize Strict State."""
    logger = LogHandler(pool)
    thread_id = config["configurable"]["thread_id"]
    config["configurable"].get("user_id")
    checkpoint_id = config["configurable"].get("checkpoint_id")

    request = state.get("input_request", "")

    # Security: Mask PII in the input request immediately (using global import)
    request = mask_pii(request)

    await logger.log_step(thread_id, "preprocess", "info", f"Validating: {request}", checkpoint_id)

    if not request:
        return {"errors": ["No input provided"]}

    # Gatekeeper Logic (Simplified for brevity, can move to service later)
    # For now, we assume valid and just format timestamp
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    refined_request = f"{request} (Time: {current_time})"

    await logger.log_step(thread_id, "preprocess", "output", "Approved\n\n", checkpoint_id)
    # Log User Input as Message for Chat UI
    await logger.log_step(thread_id, "preprocess", "message", request, checkpoint_id)

    # Initialize Strict Lists if they don't exist
    return {
        "input_request": refined_request,
        "messages": [HumanMessage(content=request)],  # Start conversation
        "tasks": [],
        "results": [],
        "context": f"Request validated at {current_time}",
    }


async def supervisor_node(state: GraphState, config: RunnableConfig, allowed_node_names: list[str] | None = None) -> dict:
    """Decide next steps using OrchestratorService."""
    logger = LogHandler(pool)
    thread_id = config["configurable"]["thread_id"]
    user_id = config["configurable"].get("user_id")
    checkpoint_id = config["configurable"].get("checkpoint_id")

    # Adapt State to Service Contracts
    # We reconstruct AgentResults from state['results'] which are dicts
    history = [AgentResult(**r) for r in state.get("results", [])]
    
    # Log context
    log_msg = "Orchestrating..."
    if allowed_node_names:
        log_msg += f" [Restricted to: {allowed_node_names}]"

    await logger.log_step(thread_id, "supervisor", "info", log_msg, checkpoint_id)

    next_agent_names = await orchestrator_service.decide_next_step(
        request=state["input_request"],
        history=history,
        context=state.get("context", ""),
        trace_id=thread_id,
        user_id=user_id,
        allowed_node_names=allowed_node_names,
    )

    await logger.log_step(thread_id, "supervisor", "output", f"Decided: {next_agent_names}\n", checkpoint_id)

    # Convert decisions into Pending Tasks
    new_tasks = []
    for name in next_agent_names:
        if name in ["qa", "tool_planning"]:
            continue  # Special handling logic in graph edges
        
        # Create a new Task for this agent
        task = AgentTask(
            id=str(uuid.uuid4()),
            type="crew",
            name=name,
            input_data=state["input_request"],  # Default to full request, logic can refine this
            assigned_to=name,
        )
        new_tasks.append(task.model_dump())

    return {
        "next_step": next_agent_names,
        "tasks": new_tasks,  # Log that we assigned these
    }


async def execute_agent_node(state: GraphState, config: RunnableConfig, agent_name: str) -> dict:
    """Execute a generic agent using CrewService."""
    logger = LogHandler(pool)
    thread_id = config["configurable"]["thread_id"]
    user_id = config["configurable"].get("user_id")
    checkpoint_id = config["configurable"].get("checkpoint_id")

    await logger.log_step(thread_id, agent_name, "info", "Executing...", checkpoint_id)

    # Find the Task Logic:
    # Ideally, the Supervisor assigned a specific Task ID.
    # But for parallel execution in LangGraph, we just know 'agent_name' is running.
    # We find the *latest pending task* for this agent.

    # Filter tasks dicts to find one for this agent that is 'pending' (implementation detail: status check?)
    # For now, we create an ad-hoc task wrapper if needed, or find the last one.
    # Simpler: Create a Task object on the fly representing "Run Now".

    current_task = AgentTask(
        id=str(uuid.uuid4()),
        type="crew",
        name=agent_name,
        input_data=state["input_request"],
        assigned_to=agent_name,
    )

    try:
        # DEBUG LOG START
        with open("/app/backend/src/debug_nodes.log", "a") as f:
            f.write(f"Starting execution for {agent_name}\n")
            
        # Prepare Infra
        # We assume thread_id is enough to scope the workspace.
        infra_config = infrastructure_service.get_or_create_infrastructure(thread_id)


        # Execution Loop (with Optional Reflection)
        max_retries = 1
        attempt = 0
        final_result = None
        reflection_feedback = None

        # Check if agent has reflection enabled
        registry = AgentRegistry()
        agent_config = registry.get_config(agent_name)
        use_reflection = agent_config.agent.use_reflection if agent_config else False
        agent_role = agent_config.agent.role if agent_config else agent_name

        # VOYAGER: Pre-Execution Skill Retrieval
        skill_context = ""
        try:
            retrieved_skills = await skill_service.retrieve_skills(
                query=state["input_request"],
                agent_role=agent_role,
                k=3,
                similarity_threshold=0.7
            )
            if retrieved_skills:
                skill_context = "\n\nPAST SUCCESSFUL SOLUTIONS (Use as reference):\n"
                for i, skill in enumerate(retrieved_skills, 1):
                    skill_context += f"\n--- Skill {i} ---\n"
                    skill_context += f"Task: {skill.task_description[:200]}...\n"
                    skill_context += f"Solution: {skill.solution_code[:500]}...\n"
                await logger.log_step(thread_id, agent_name, "thought", f"Retrieved {len(retrieved_skills)} similar skills from library.", checkpoint_id)
        except Exception as skill_err:
            await logger.log_step(thread_id, agent_name, "thought", f"Skill retrieval skipped: {skill_err}", checkpoint_id)

        while attempt <= max_retries:
            attempt += 1
            
            # If retrying, append reflection feedback to context
            execution_context = state.get("context", "") + skill_context
            if attempt > 1 and reflection_feedback:
                 execution_context += f"\n\nCRITIQUE & FEEDBACK (Please fix):\n{reflection_feedback}"

            result = await crew_service.execute_task(
                task=current_task,
                context=execution_context,
                infra=infra_config,
                trace_id=thread_id,
                user_id=user_id,
            )
            final_result = result

            if not use_reflection or attempt > max_retries:
                break
            
            # Perform Reflection
            from crew.agents import llm
            reflection_prompt = f"""
            Review the following agent output for the user request: "{state["input_request"]}"
            
            Agent Output:
            {result.raw_output}
            
            Identify any logical errors, missing requirements, or hallucinations.
            If the output is good and meets the request, reply with "APPROVED".
            If there are issues, provide concise, actionable feedback for the agent to fix them.
            """
            
            critique = await llm.acall(reflection_prompt)
            
            if "APPROVED" in critique.upper():
                await logger.log_step(thread_id, agent_name, "thought", "Self-Correction: Output verified and approved.", checkpoint_id)
                break
            else:
                reflection_feedback = critique
                await logger.log_step(thread_id, agent_name, "thought", f"Self-Correction Triggered: {critique}", checkpoint_id)
                # Loop continues to retry with feedback

        # Use the final result from the loop
        result = final_result


        # Log the actual content for history (Masked)
        masked_summary = mask_pii(result.summary)
        masked_raw = mask_pii(result.raw_output)

        # Update metadata with more details if needed
        # Ensuring we pass metadata to all logs where logical
        log_metadata = result.metadata

        await logger.log_step(
            thread_id,
            agent_name,
            "thought",
            masked_summary,
            checkpoint_id,
            metadata=log_metadata,
        )

        # Log as a Message for Chat UI (Masked)
        await logger.log_step(
            thread_id,
            agent_name,
            "message",  # New type for Chat UI
            masked_summary,
            checkpoint_id,
            metadata=log_metadata,
        )

        await logger.log_step(
            thread_id,
            agent_name,
            "output",
            f"Done. {masked_summary[:100]}",
            checkpoint_id,
            metadata=log_metadata,
        )

        # IMPORTANT: Return masked results so the downstream nodes (Graph State)
        # only ever contain safe DTOs.
        result_dump = result.model_dump()
        result_dump["summary"] = masked_summary
        result_dump["raw_output"] = masked_raw

        # DyLAN Feedback Loop: Update success rate on completion
        registry = AgentRegistry()
        await registry.update_agent_success_rate(agent_name, success=True)

        # VOYAGER: Post-Execution Skill Saving (async, fire-and-forget)
        try:
            await skill_service.add_skill(
                agent_role=agent_role,
                task_description=state["input_request"],
                solution_code=result.raw_output
            )
            await logger.log_step(thread_id, agent_name, "thought", "Skill saved to library.", checkpoint_id)
        except Exception as skill_save_err:
            await logger.log_step(thread_id, agent_name, "thought", f"Skill save skipped: {skill_save_err}", checkpoint_id)

        return {
            "results": [result_dump],
            "messages": [AIMessage(content=result.summary, name=agent_name)],
            "context": f"\n\nAgent {agent_name} Findings:\n{masked_raw[:20000]}",
        }

    except Exception as e:
        # DEBUG LOG ERROR
        try:
            with open("/app/backend/src/debug_nodes.log", "a") as f:
                f.write(f"Error executing {agent_name}: {e}\n")
        except Exception:
            pass
            
        await logger.log_step(thread_id, agent_name, "error", str(e), checkpoint_id)
        
        # DyLAN Feedback Loop: Update success rate on failure
        registry = AgentRegistry()
        await registry.update_agent_success_rate(agent_name, success=False)
        # CRITICAL FIX: Return a failure result so the Orchestrator knows this agent failed.
        # This prevents infinite loops where the Orchestrator sees no history and retries the same agent.
        failure_result = AgentResult(
            task_id=str(uuid.uuid4()),
            summary=f"Execution Failed: {str(e)}",
            raw_output=str(e),
            metadata={"error": True, "agent": agent_name},
            timestamp=datetime.now()
        )
        
        return {
            "results": [failure_result.model_dump()],
            "errors": [str(e)],
            "context": f"\n\nAgent {agent_name} Failed:\n{str(e)}"
        }


async def execute_workflow_node(state: GraphState, config: RunnableConfig, workflow_name: str) -> dict:
    """
    Execute a Superagent Team (Workflow) as a subgraph.
    Dynamic recursive execution.
    """
    logger = LogHandler(pool)
    thread_id = config["configurable"]["thread_id"]
    checkpoint_id = config["configurable"].get("checkpoint_id")
    
    await logger.log_step(thread_id, f"TEAM_{workflow_name}", "info", f"Initializing Team {workflow_name}...", checkpoint_id)

    # 1. Load Workflow Config
    registry = AgentRegistry()
    workflows = registry.get_workflows()
    target_workflow = next((w for w in workflows if w.name == workflow_name), None)
    
    if not target_workflow:
        error_msg = f"Workflow {workflow_name} not found."
        await logger.log_step(thread_id, f"TEAM_{workflow_name}", "error", error_msg, checkpoint_id)
        return {"errors": [error_msg]}

    try:
        # 2. Build Subgraph on the fly
        from functools import partial

        from langgraph.graph import END, Send, StateGraph
        
        subgraph = StateGraph(GraphState)
        
        # Track supervisor info to build conditional edges later
        supervisor_present = False
        supervisor_map = {}
        
        # Calculate Allowed nodes for this team (Constraint)
        # We need ALL legal nodes in this graph (except maybe supervisor itself, 
        # but Orchestrator treats "supervisor" as the one calling, it outputs names of OTHERS)
        team_agent_names = [n.type for n in target_workflow.nodes if n.type != "supervisor"]

        # Add Nodes
        node_ids = []
        for node in target_workflow.nodes:
            if node.type == "supervisor":
                # Bind the Logic with constraints
                # partial(supervisor_node, allowed_node_names=...)
                subgraph.add_node(
                    node.id, 
                    partial(supervisor_node, allowed_node_names=team_agent_names)
                )
                supervisor_present = True
            else:
                # Regular Agent
                # 'node.type' is the agent name in registry
                subgraph.add_node(node.id, partial(execute_agent_node, agent_name=node.type))
            
            node_ids.append(node.id)
            
        # Add Edges
        # If supervisor is present, we must treat edges STARTING from supervisor as POTENTIAL routes (Conditional).
        # Edges ENDING at supervisor are normal (Loop back).
        
        for edge in target_workflow.edges:
            source = edge.source
            target = edge.target
            
            if source == "supervisor" and supervisor_present:
                # This is a candidate route for the supervisor.
                # We expect the Supervisor to return 'next_step': target
                # So we add it to the map.
                if target == "END":
                     # Handle explicit end
                     supervisor_map["END"] = END
                else:
                     supervisor_map[target] = target
            else:
                # Standard Hard Edge (e.g. Agent -> Supervisor)
                if target == "END":
                     subgraph.add_edge(source, END)
                else:
                     subgraph.add_edge(source, target)
        
        # Special Logic: If supervisor is present, add the one Conditional Edge
        if supervisor_present:
            # We need a routing function that looks at state['next_step']
            # We can reuse 'supervisor_decision' from graph.py if we import it or define a lambda
            # But 'supervisor_decision' logic is generic: returns state.get("next_step")
            
            # We define a local helper or import it?
            # Let's import the logic or replicate simple version strictly for this subgraph
            
            def subgraph_router(state: GraphState):
                next_steps = state.get("next_step", [])
                if not next_steps:
                    return END # Default to END if stuck
                
                # Check if it matches our map
                if isinstance(next_steps, list):
                     # If strictly one
                     if len(next_steps) == 1:
                         return next_steps[0]
                     return [Send(n, state) for n in next_steps]
                return next_steps

            # Ensure we have an END route in the map just in case
            if "END" not in supervisor_map:
                supervisor_map["END"] = END
            if "finish" not in supervisor_map: # Common LLM token
                supervisor_map["finish"] = END
            # Also map 'QA' to END if the inner supervisor decides 'QA' 
            # (which means "I'm done" in the Orchestrator logic)
            if "qa" not in supervisor_map:
                 supervisor_map["qa"] = END
                
            subgraph.add_conditional_edges(
                "supervisor",
                subgraph_router,
                supervisor_map
            )
                 
        # Set Entry Point
        # If supervisor is present, it is usually the entry point?
        # Or do we look for the node with no incoming edges?
        # Architect usually puts Supervisor first.
        if "supervisor" in node_ids:
            subgraph.set_entry_point("supervisor")
        elif node_ids:
            subgraph.set_entry_point(node_ids[0])
            
        # 3. Compile and Run
        # We don't checkpoint subgraphs separately to avoid state fragmentation, 
        # or we could share the checkpointer? 
        # For now, memory-only execution for the sub-step is safer/faster.
        compiled_subgraph = subgraph.compile()
        
        await logger.log_step(thread_id, f"TEAM_{workflow_name}", "info", "Executing Team Logic...", checkpoint_id)
        
        # We invoke with the SAME state. 
        # CAUTION: Infinite recursion if a team calls itself.
        final_state = await compiled_subgraph.ainvoke(state, config=config)
        
        # 4. Extract Results (Delta only)
        # We must return ONLY what was added to prevent duplication in the parent graph
        
        initial_results_len = len(state.get("results", []))
        initial_messages_len = len(state.get("messages", []))
        initial_context = state.get("context") or ""
        
        final_results = final_state.get("results", [])
        final_messages = final_state.get("messages", [])
        final_context = final_state.get("context") or ""
        
        new_results = final_results[initial_results_len:]
        new_messages = final_messages[initial_messages_len:]
        
        # Calculate Context Delta
        # Subgraph starts with 'initial_context', appends updates via reduce_str.
        # So final_context should start with initial_context.
        new_context = ""
        if len(final_context) > len(initial_context):
            new_context = final_context[len(initial_context):]
            
            # Clean up potential double separators from reduce_str
            # If initial_context was not empty, reduce_str added "\n\n" before the new content.
            # We want to keep that cleaner or let the parent handle it?
            # Parent: reduce_str(Initial, Delta) -> Initial + "\n\n" + Delta
            # If Delta starts with "\n\n", we get "\n\n\n\n".
            # So we strip leading/trailing whitespace from the Delta to be safe.
            new_context = new_context.strip()
        
        await logger.log_step(thread_id, f"TEAM_{workflow_name}", "output", "Team Execution Complete.", checkpoint_id)
        
        return {
            "results": new_results,
            "context": new_context,
            "messages": new_messages
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        await logger.log_step(thread_id, f"TEAM_{workflow_name}", "error", str(e), checkpoint_id)
        return {"errors": [f"Team Execution Failed: {str(e)}"]}
async def tool_planning_node(state: GraphState, config: RunnableConfig) -> dict:
    """Legacy Tool Planning (Wrapped)."""
    # ... keeping "lite" version for now or implementing strict ToolService later
    # For this refactor step, we map it to 'context' updates.
    logger = LogHandler(pool)
    thread_id = config["configurable"]["thread_id"]

    checkpoint_id = config["configurable"].get("checkpoint_id")

    await logger.log_step(thread_id, "tool_planning", "info", "Planning Tool...", checkpoint_id)

    # (Placeholder for complex tool logic - returning dummy for flow test)
    # Ideally: Call ToolService.plan()

    # Removed legacy CrewAgents usage.
    # Future: Use AgentRegistry if we need to plan using specific agent tools.

    return {"tool_call": None}  # Skip tools for strict pass or fix later


async def tool_execution_node(state: GraphState, config: RunnableConfig) -> dict:
    return {}  # Placeholder


async def qa_node(state: GraphState, config: RunnableConfig) -> dict:
    """Final QA using strict context."""
    logger = LogHandler(pool)
    thread_id = config["configurable"]["thread_id"]
    user_id = config["configurable"].get("user_id")
    checkpoint_id = config["configurable"].get("checkpoint_id")

    await logger.log_step(thread_id, "qa", "info", "Finalizing...", checkpoint_id)

    context = state.get("context", "")
    results = state.get("results", [])

    # Aggregate specific details
    full_context = context + "\n\nDetailed Results:\n"
    for r in results:
        full_context += f"- [{r.get('metadata', {}).get('agent_role', 'Agent')}]: {r.get('summary')}\n"

    prompt = f"""User Request: {state["input_request"]}
    
    Context (MoA Layer 1 Outputs):
    {full_context}
    
    **instructions (MoA Layer 2 - Aggregation):**
    You are the Final Aggregator in a Mixture-of-Agents system.
    1. Synthesize the findings from all agents above into a cohesive, single answer.
    2. RESOLVE CONFLICTS: If agents disagree, use your best judgment or mention the discrepancy.
    3. MERGE INSIGHTS: Combine the code/data from one agent with the analysis from another.
    4. Provide the final, polished response for the user.
    """

    # Inject Observability
    callbacks = []
    if thread_id:
        from core.observability import get_observability_callback

        callbacks.append(get_observability_callback(trace_id=thread_id, user_id=user_id, trace_name="qa_final_response"))

    response = await llm.acall(prompt, callbacks=callbacks)

    # Mask PII in final response
    masked_response = mask_pii(response)

    # Log full response as content for history
    await logger.log_step(thread_id, "qa", "thought", masked_response, checkpoint_id)

    # Log as Chat Message
    await logger.log_step(thread_id, "qa", "message", masked_response, checkpoint_id)

    await logger.log_step(thread_id, "qa", "output", "Done.", checkpoint_id)

    return {
        "final_response": response,
        "messages": [AIMessage(content=response, name="QA")],
    }
