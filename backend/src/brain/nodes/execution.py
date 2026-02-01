import asyncio
import json
import uuid
from datetime import datetime
from functools import partial

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from langgraph.types import Command, Send

from brain.logger import LogHandler

# Import supervisor for the dynamic workflow reconstruction (recursive import prevention?)
# We will import inside the function or pass it to avoid cycle if supervisor imports execution.
# Actually supervisor.py does NOT import execution.py. So it is safe to import supervisor here IF needed.
# But `execute_workflow_node` needs `supervisor_node`.
from brain.nodes.supervisor import supervisor_node
from brain.prompts import REFLECTION_PROMPT
from brain.registry import AgentRegistry
from crew.agents import llm
from models.state import AgentResult, AgentTask, GraphState
from services.crew_service import CrewService
from services.infrastructure import InfrastructureService
from services.skill_service import skill_service
from utils.pii import masker
from utils.tokens import truncate_to_token_budget

# Token budget constants
MAX_SKILL_TOKENS = 800

# Initialize Services
crew_service = CrewService()
infrastructure_service = InfrastructureService()


async def execute_agent_node(state: GraphState, config: RunnableConfig, agent_name: str) -> dict:
    """Execute a generic agent using CrewService."""
    logger = LogHandler()
    thread_id = config["configurable"]["thread_id"]
    user_id = config["configurable"].get("user_id")
    checkpoint_id = config["configurable"].get("checkpoint_id")

    await logger.log_step(thread_id, agent_name, "info", "Executing...", checkpoint_id)

    # Find the Task Logic:
    # REFACTOR: Retrieve the specific task created by Supervisor if available.
    # This preserves specific inputs/instructions passed from the Orchestrator layer.
    pending_tasks = state.get("tasks", [])
    # Find the last task assigned to this agent
    # We iterate reversed to get the most recent assignment
    current_task = None
    for t_data in reversed(pending_tasks):
        if t_data.get("assigned_to") == agent_name:
            current_task = AgentTask(**t_data)
            break

    if not current_task:
        # Fallback if no specific task found (should be rare with correct Supervisor logic)
        current_task = AgentTask(
            id=str(uuid.uuid4()),
            type="crew",
            name=agent_name,
            input_data=state["input_request"],
            assigned_to=agent_name,
        )
    else:
        await logger.log_step(
            thread_id, agent_name, "debug", f"Found pending task {current_task.id[:8]}", checkpoint_id
        )

    try:
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
                query=state["input_request"], agent_role=agent_role, k=3, similarity_threshold=0.7
            )
            if retrieved_skills:
                skill_context = "\n\nPAST SUCCESSFUL SOLUTIONS (Use as reference):\n"
                for i, skill in enumerate(retrieved_skills, 1):
                    skill_context += f"\n--- Skill {i} ---\n"
                    skill_context += f"Task: {skill.task_description[:150]}...\n"
                    skill_context += f"Solution: {skill.solution_code[:300]}...\n"
                # Apply token budget to prevent context overflow
                skill_context = truncate_to_token_budget(skill_context, MAX_SKILL_TOKENS)
                await logger.log_step(
                    thread_id,
                    agent_name,
                    "thought",
                    f"Retrieved {len(retrieved_skills)} similar skills from library.",
                    checkpoint_id,
                )
        except Exception as skill_err:
            await logger.log_step(
                thread_id, agent_name, "thought", f"Skill retrieval skipped: {skill_err}", checkpoint_id
            )

        # WORKER LAYER STRATEGY: Ephemeral Context
        # Worker sees: global_state KEYS (Knowledge of existence) + specific task input + skills.
        # Worker does NOT see: Full conversation history or Full Artifact Content (Congestion).

        # We provide a menu of available artifacts so the agent knows what to read.
        artifact_keys = [k for k in state.get("global_state", {}).keys() if not k.startswith("_meta")]
        available_artifacts_str = ", ".join(artifact_keys) if artifact_keys else "None"

        # Inject Recent History (Blindness Fix)
        messages = state.get("messages", [])
        recent_history = ""
        if messages:
            for m in messages[-5:]:
                # Handle generic Message objects or dicts
                role = getattr(m, "type", "unknown")
                content = getattr(m, "content", str(m))
                recent_history += f"\n[{role.upper()}]: {content}"

        base_context = (
            f"AVAILABLE ARTIFACTS (Use tools to read if needed): [{available_artifacts_str}]\n"
            f"RECENT CONVERSATION HISTORY:{recent_history}\n"
            f"{skill_context}"
        )

        while attempt <= max_retries:
            attempt += 1

            # If retrying, append reflection feedback to context
            execution_context = base_context
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
            reflection_prompt = REFLECTION_PROMPT.format(
                input_request=state["input_request"], raw_output=result.raw_output
            )

            # Inject observability callbacks for reflection call
            reflection_callbacks = []
            if thread_id:
                from core.observability import get_observability_callback

                reflection_callbacks.append(
                    get_observability_callback(
                        trace_id=thread_id, user_id=user_id, trace_name=f"reflection_{agent_name}"
                    )
                )

            critique_raw = await llm.acall(reflection_prompt, callbacks=reflection_callbacks)

            # Robust JSON Parsing for Tri-State Reflection
            try:
                # Clean markdown blocks if present
                critique_clean = critique_raw.replace("```json", "").replace("```", "").strip()
                critique_json = json.loads(critique_clean)

                status = critique_json.get("status", "REJECTED").upper()

                if status == "APPROVED":
                    await logger.log_step(
                        thread_id,
                        agent_name,
                        "thought",
                        "Self-Correction: Output verified and approved.",
                        checkpoint_id,
                    )
                    break

                elif status == "FIXED":
                    # Agent Reflector fixed it instantly
                    refined_output = critique_json.get("refined_output")
                    if refined_output:
                        # Update the result object in-place
                        result.raw_output = refined_output
                        result.summary = refined_output[:4000] + "..." if len(refined_output) > 4000 else refined_output
                        await logger.log_step(
                            thread_id,
                            agent_name,
                            "thought",
                            "Self-Correction: Output FIXED by Auto-Reflector.",
                            checkpoint_id,
                        )
                        final_result = result  # Ensure final result uses the fixed version
                        break
                    else:
                        reflection_feedback = "Reflector status was FIXED but refined_output was null. Please retry."

                else:  # REJECTED or anything else
                    reflection_feedback = critique_json.get("feedback", "No feedback provided.")
                    await logger.log_step(
                        thread_id,
                        agent_name,
                        "thought",
                        f"Self-Correction Triggered: {reflection_feedback}",
                        checkpoint_id,
                    )

            except Exception as e:
                # Fallback for parsing errors
                await logger.log_step(
                    thread_id,
                    agent_name,
                    "warning",
                    f"Reflection JSON Parse Error: {e}. Raw: {critique_raw[:50]}",
                    checkpoint_id,
                )
                if "APPROVED" in critique_raw.upper():
                    break
                reflection_feedback = f"Reflection format error. Ensure valid JSON. Raw output: {critique_raw}"
                # Loop continues to retry with feedback

        # Use the final result from the loop
        result = final_result

        # Log the actual content for history (Masked)
        # FORCE GROUNDING: Explicitly label success so Orchestrator knows the action happened.
        masked_summary = f"✅ [SUCCESS] {masker.mask(result.summary)}"
        masked_raw = masker.mask(result.raw_output)

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
                agent_role=agent_role, task_description=state["input_request"], solution_code=result.raw_output
            )
            await logger.log_step(thread_id, agent_name, "thought", "Skill saved to library.", checkpoint_id)
        except Exception as skill_save_err:
            await logger.log_step(
                thread_id, agent_name, "thought", f"Skill save skipped: {skill_save_err}", checkpoint_id
            )

        return {
            "results": [result_dump],
            "messages": [AIMessage(content=masked_summary, name=agent_name)],
            "context": f"\n\nAgent {agent_name} Findings:\n{masked_raw[:20000]}",
        }

    except asyncio.CancelledError:
        msg = "🚫 [CANCELLED] Execution stopped by user or timeout."
        await logger.log_step(thread_id, agent_name, "warning", msg, checkpoint_id)
        # We must re-raise CancelledError for LangGraph/Asyncio to handle it correctly
        raise

    except Exception as e:
        await logger.log_step(thread_id, agent_name, "error", str(e), checkpoint_id)

        # DyLAN Feedback Loop: Update success rate on failure
        registry = AgentRegistry()
        await registry.update_agent_success_rate(agent_name, success=False)

        failure_result = AgentResult(
            task_id=str(uuid.uuid4()),
            summary=f"❌ [FAILED] {str(e)}",
            raw_output=str(e),
            assigned_to=agent_name,
            metadata={"error": True, "agent": agent_name},
            timestamp=datetime.now(),
        )

        return {
            "results": [failure_result.model_dump()],
            "errors": [str(e)],
            "context": f"\n\nAgent {agent_name} Failed:\n{str(e)}",
        }


async def execute_workflow_node(state: GraphState, config: RunnableConfig, workflow_name: str) -> dict:
    """
    Execute a Superagent Team (Workflow) as a subgraph.
    Dynamic recursive execution.
    """
    logger = LogHandler()
    thread_id = config["configurable"]["thread_id"]
    checkpoint_id = config["configurable"].get("checkpoint_id")

    await logger.log_step(
        thread_id, f"TEAM_{workflow_name}", "info", f"Initializing Team {workflow_name}...", checkpoint_id
    )

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
        subgraph = StateGraph(GraphState)

        # Build Mapping: Agent Type (Name) -> Node ID
        type_to_id = {
            node.type: node.id
            for node in target_workflow.nodes
            if node.id.lower() != "supervisor" and node.type.lower() != "supervisor"
        }
        # Explicit mappings for static/special nodes
        type_to_id["qa"] = END
        type_to_id["tool_planning"] = "tool_planning"  # If present in subgraph

        team_agent_names = list(type_to_id.keys())

        # 3. Add Nodes
        node_ids = []

        for node in target_workflow.nodes:
            if node.id.lower() == "supervisor" or node.type.lower() == "supervisor":
                # WRAPPER: Intercept Command -> Map IDs
                async def mapped_supervisor_node(state: GraphState, config: RunnableConfig) -> Command:
                    # 1. Call real supervisor
                    cmd = await supervisor_node(state, config, allowed_node_names=team_agent_names)

                    # 2. Map 'goto' targets
                    if isinstance(cmd, Command):
                        original_goto = cmd.goto
                        new_goto = []

                        # Normalize to list
                        targets = original_goto if isinstance(original_goto, list) else [original_goto]

                        for t in targets:
                            # Handle Send objects
                            if isinstance(t, Send):
                                # t.node is the target name
                                mapped_id = type_to_id.get(t.node, t.node)
                                new_goto.append(Send(mapped_id, t.arg))
                            elif isinstance(t, str):
                                mapped_id = type_to_id.get(t, t)
                                if mapped_id == END:
                                    # Command(goto=END) is valid
                                    new_goto.append(END)
                                else:
                                    new_goto.append(mapped_id)

                        # 3. Return new Command
                        return Command(goto=new_goto, update=cmd.update)
                    return cmd

                subgraph.add_node(node.id, mapped_supervisor_node)
            else:
                # Regular Agent
                subgraph.add_node(node.id, partial(execute_agent_node, agent_name=node.type))

            node_ids.append(node.id)

        # 4. Add Edges (Only Hard Edges needed now)
        for edge in target_workflow.edges:
            source = edge.source
            target = edge.target

            # Edges STARTING from supervisor are now handled by Command logic implicitly.
            # We ONLY add edges not involving supervisor as source (e.g. Agent -> Supervisor).
            if source.lower() != "supervisor":
                if target == "END":
                    subgraph.add_edge(source, END)
                else:
                    subgraph.add_edge(source, target)

        # Set Entry Point
        if "supervisor" in node_ids:
            subgraph.set_entry_point("supervisor")
        elif node_ids:
            subgraph.set_entry_point(node_ids[0])

        # 5. Compile and Run
        # We don't checkpoint subgraphs separately to avoid state fragmentation
        compiled_subgraph = subgraph.compile()

        await logger.log_step(thread_id, f"TEAM_{workflow_name}", "info", "Executing Team Logic...", checkpoint_id)

        # We invoke with the SAME state.
        final_state = await compiled_subgraph.ainvoke(state, config=config)

        # 6. Extract Results (Delta only)
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
        new_context = ""
        if len(final_context) > len(initial_context):
            new_context = final_context[len(initial_context) :]
            new_context = new_context.strip()

        await logger.log_step(thread_id, f"TEAM_{workflow_name}", "output", "Team Execution Complete.", checkpoint_id)

        return {"results": new_results, "context": new_context, "messages": new_messages}

    except Exception as e:
        import traceback

        traceback.print_exc()
        await logger.log_step(thread_id, f"TEAM_{workflow_name}", "error", str(e), checkpoint_id)
        return {"errors": [f"Team Execution Failed: {str(e)}"]}
