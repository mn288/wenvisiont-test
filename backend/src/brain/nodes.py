import uuid
from datetime import datetime

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from src.brain.logger import LogHandler
from src.core.database import pool
from src.crew.agents import llm
from src.models.state import AgentResult, AgentTask, GraphState
from src.services.crew import CrewService
from src.services.infrastructure import InfrastructureService
from src.services.orchestrator import OrchestratorService

# Initialize Services
orchestrator_service = OrchestratorService()
crew_service = CrewService()
infrastructure_service = InfrastructureService()


async def preprocess_node(state: GraphState, config: RunnableConfig) -> dict:
    """Validate input and initialize Strict State."""
    logger = LogHandler(pool)
    thread_id = config["configurable"]["thread_id"]
    checkpoint_id = config["configurable"].get("checkpoint_id")

    request = state.get("input_request", "")
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


async def supervisor_node(state: GraphState, config: RunnableConfig) -> dict:
    """Decide next steps using OrchestratorService."""
    logger = LogHandler(pool)
    thread_id = config["configurable"]["thread_id"]
    checkpoint_id = config["configurable"].get("checkpoint_id")

    # Adapt State to Service Contracts
    # We reconstruct AgentResults from state['results'] which are dicts
    history = [AgentResult(**r) for r in state.get("results", [])]

    await logger.log_step(thread_id, "supervisor", "info", "Orchestrating...", checkpoint_id)

    next_agent_names = await orchestrator_service.decide_next_step(
        request=state["input_request"],
        history=history,
        context=state.get("context", ""),
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
        # Prepare Infra
        # We assume thread_id is enough to scope the workspace.
        infra_config = infrastructure_service.get_or_create_infrastructure(thread_id)

        result = await crew_service.execute_task(
            task=current_task, context=state.get("context", ""), infra=infra_config
        )

        # Log the actual content for history
        await logger.log_step(
            thread_id,
            agent_name,
            "thought",
            result.summary,
            checkpoint_id,
        )

        # Log as a Message for Chat UI
        await logger.log_step(
            thread_id,
            agent_name,
            "message",  # New type for Chat UI
            result.summary,
            checkpoint_id,
        )

        await logger.log_step(
            thread_id,
            agent_name,
            "output",
            f"Done. {result.summary[:100]}",
            checkpoint_id,
        )

        return {
            "results": [result.model_dump()],
            "messages": [AIMessage(content=result.summary, name=agent_name)],
            "context": f"\n\nAgent {agent_name} Findings:\n{result.summary}",
        }

    except Exception as e:
        await logger.log_step(thread_id, agent_name, "error", str(e), checkpoint_id)
        return {"errors": [str(e)]}


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
    checkpoint_id = config["configurable"].get("checkpoint_id")

    await logger.log_step(thread_id, "qa", "info", "Finalizing...", checkpoint_id)

    context = state.get("context", "")
    results = state.get("results", [])

    # Aggregate specific details
    full_context = context + "\n\nDetailed Results:\n"
    for r in results:
        full_context += f"- [{r.get('metadata', {}).get('agent_role', 'Agent')}]: {r.get('summary')}\n"

    prompt = f"""User Request: {state["input_request"]}
    
    Context:
    {full_context}
    
    Provide a final answer."""

    response = await llm.acall(prompt)

    # Log full response as content for history
    await logger.log_step(thread_id, "qa", "thought", response, checkpoint_id)

    # Log as Chat Message
    await logger.log_step(thread_id, "qa", "message", response, checkpoint_id)

    await logger.log_step(thread_id, "qa", "output", "Done.", checkpoint_id)

    return {
        "final_response": response,
        "messages": [AIMessage(content=response, name="QA")],
    }
