from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from brain.logger import LogHandler
from brain.prompts import QA_AGGREGATION_PROMPT
from core.database import pool
from crew.agents import llm
from models.state import GraphState
from utils.pii import masker


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
    # Aggregate specific details
    full_context = context + "\n\nDetailed Results:\n"
    for r in results:
        # Expect r to be a dict (serialized AgentResult)
        agent = r.get("assigned_to", "Unknown Agent")
        summary = r.get("summary", "No summary provided.")
        # We can also check if there are artifacts to mention
        artifacts = r.get("artifacts", [])
        artifact_note = f" (Produced {len(artifacts)} artifacts)" if artifacts else ""

        full_context += f"\n### Result from {agent}{artifact_note}:\n{summary}\n"

    prompt = QA_AGGREGATION_PROMPT.format(input_request=state["input_request"], full_context=full_context)

    # Inject Observability & Streaming
    # usage: Prepare a RunnableConfig that merges the graph's config with our custom callbacks
    # This prevents 'multiple values for parent_run_id' errors and 'run_inline' errors.

    run_config = config.copy() if config else {}

    # 1. Prepare Custom Callbacks to Add
    custom_callbacks = []
    if llm.callbacks:
        custom_callbacks.extend(llm.callbacks)

    if thread_id:
        from core.observability import get_observability_callback

        custom_callbacks.append(
            get_observability_callback(trace_id=thread_id, user_id=user_id, trace_name="qa_final_response")
        )

    # 2. Merge into run_config
    existing_callbacks = run_config.get("callbacks")

    if existing_callbacks:
        if isinstance(existing_callbacks, list):
            # It's a list: Copy and extend
            run_config["callbacks"] = existing_callbacks + custom_callbacks
        elif hasattr(existing_callbacks, "add_handler"):
            # It's a CallbackManager: Add handlers to it
            # Note: This mutates the manager for this scope, which is generally what we want for this node execution.
            for cb in custom_callbacks:
                existing_callbacks.add_handler(cb)
            # No need to re-set run_config["callbacks"], it's the same object reference
        else:
            # Fallback: Just ignore existing if unknown type (safe default)
            run_config["callbacks"] = custom_callbacks
    else:
        run_config["callbacks"] = custom_callbacks

    # Use client.ainvoke directly to ensure proper Runnable contract
    response_msg = await llm.client.ainvoke([HumanMessage(content=prompt)], config=run_config)
    response = response_msg.content

    # Mask PII in final response
    masked_response = masker.mask(response)

    # Log full response as content for history
    await logger.log_step(thread_id, "qa", "thought", masked_response, checkpoint_id)

    # Log as Chat Message
    await logger.log_step(thread_id, "qa", "message", masked_response, checkpoint_id)

    await logger.log_step(thread_id, "qa", "output", "Done.", checkpoint_id)

    return {
        "final_response": response,
        "messages": [AIMessage(content=response, name="QA")],
    }
