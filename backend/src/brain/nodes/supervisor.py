import uuid
from datetime import datetime

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command, Send

from brain.logger import LogHandler
from models.state import AgentTask, GraphState
from services.orchestrator import OrchestratorService
from utils.pii import masker

# Initialize Services
orchestrator_service = OrchestratorService()


async def preprocess_node(state: GraphState, config: RunnableConfig) -> dict:
    """Validate input and initialize Hybrid Context State."""
    logger = LogHandler()
    thread_id = config["configurable"]["thread_id"]
    checkpoint_id = config["configurable"].get("checkpoint_id")

    request = state.get("input_request", "")

    # Security: Mask PII
    request = masker.mask(request)

    await logger.log_step(thread_id, "preprocess", "info", f"Validating: {request}", checkpoint_id)

    if not request:
        return {"errors": ["No input provided"]}

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    refined_request = f"{request} (Time: {current_time})"

    await logger.log_step(thread_id, "preprocess", "output", "Approved\n\n", checkpoint_id)
    await logger.log_step(thread_id, "preprocess", "message", request, checkpoint_id)

    # Initialize Hybrid State
    return {
        "input_request": refined_request,
        "messages": [HumanMessage(content=request)],  # Keep for LangChain compatibility
        "conversation_buffer": [f"User: {request}"],  # Hybrid Arc: Active Buffer
        "global_state": {"_meta_processed_count": 0, "original_request": request},  # Hybrid Arc: State
        "long_term_summary": "",  # Hybrid Arc: LTM
        "tasks": [],
        "results": [],
        "context": f"Request validated at {current_time}",
    }


async def supervisor_node(
    state: GraphState, config: RunnableConfig, allowed_node_names: list[str] | None = None
) -> Command:
    """Decide next steps using OrchestratorService and Hybrid Context."""
    logger = LogHandler()
    thread_id = config["configurable"]["thread_id"]
    user_id = config["configurable"].get("user_id")
    checkpoint_id = config["configurable"].get("checkpoint_id")

    # --- 1. HYBRID CONTEXT: REMOVED (Handled by LangGraph Reducers) ---
    # We rely on 'global_state' and 'messages' being updated by the nodes themselves via the return value.

    current_global_state = state.get("global_state", {})
    # Convert BaseMessage list to string buffer for Orchestrator consumability
    messages = state.get("messages", [])
    conversation_buffer = []

    # Simple conversion of last N messages to string format
    # Optimization: Could move this logic to a util or the Orchestrator itself
    MAX_BUFFER_MSG = 10
    recent_messages = messages[-MAX_BUFFER_MSG:] if messages else []
    for m in recent_messages:
        role = m.type if hasattr(m, "type") else "unknown"
        name = getattr(m, "name", None)
        content = m.content if hasattr(m, "content") else str(m)

        prefix = f"{role} ({name})" if name else role
        conversation_buffer.append(f"{prefix}: {content}")

    current_summary = state.get("context", "") or ""

    # --- 3. ORCHESTRATOR (PLANNER-EXECUTOR) ---
    current_plan = state.get("plan", [])

    # Log the orchestration attempt
    await logger.log_step(
        thread_id,
        "supervisor",
        "thought",
        f"Orchestrating next step based on global state and {len(messages)} messages...",
        checkpoint_id,
    )

    next_agent_names, new_plan = await orchestrator_service.decide_next_step(
        request=state["input_request"],
        global_state=current_global_state,
        long_term_summary=current_summary,
        conversation_buffer=conversation_buffer,
        current_plan=current_plan,
        last_agent_name=state.get("last_agent"),
        trace_id=thread_id,
        user_id=user_id,
        allowed_node_names=allowed_node_names,
    )

    # Log the decision
    await logger.log_step(thread_id, "supervisor", "info", f"Routing to: {next_agent_names}", checkpoint_id)

    # Validate output
    valid_names = []
    if isinstance(next_agent_names, list):
        valid_names = [n for n in next_agent_names if n and n.lower() != "undefined"]
    elif isinstance(next_agent_names, str) and next_agent_names.lower() != "undefined":
        valid_names = [next_agent_names]

    if not valid_names:
        valid_names = ["qa"]

    # --- 4. RELIABILITY: CIRCUIT BREAKER ---
    last_agent = state.get("last_agent")
    current_retry_count = state.get("retry_count", 0)

    if len(valid_names) == 1 and valid_names[0] == last_agent:
        current_retry_count += 1
    else:
        current_retry_count = 0

    if current_retry_count >= 2:
        msg = f"⚠️ CIRCUIT BREAKER: Agent '{last_agent}' looping. Routing to QA."
        await logger.log_step(thread_id, "supervisor", "warning", msg, checkpoint_id)
        valid_names = ["qa"]
        current_retry_count = 0

    # --- 5. STATE UPDATES ---
    state_updates = {
        "next_step": valid_names,
        "last_agent": valid_names[0] if valid_names else None,
        "retry_count": current_retry_count,
        "plan": new_plan,  # Updates persistent Plan
    }

    # Convert decisions into Pending Tasks
    new_tasks = []
    destinations = []

    # Handoff Layer: Pass Global State (or subset)
    # The Orchestrator decides names, we build tasks.

    for name in valid_names:
        if name not in ["qa", "tool_planning"]:
            task = AgentTask(
                id=str(uuid.uuid4()),
                type="crew",
                name=name,
                # HANDOFF STRATEGY: Pass specific inputs if possible
                input_data=state["input_request"],  # Still passing request, but Worker should check Global State
                assigned_to=name,
            )
            new_tasks.append(task.model_dump())

        if name in ["qa", "tool_planning"]:
            destinations.append(name)
        else:
            destinations.append(Send(name, state))  # Send full state (Worker will filter)

    state_updates["tasks"] = new_tasks

    if not destinations:
        destinations = "qa"
    elif len(destinations) == 1 and not isinstance(destinations[0], Send):
        destinations = destinations[0]

    return Command(goto=destinations, update=state_updates)
