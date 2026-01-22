from typing import Optional

import orjson
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from langgraph.types import Command

from api.middleware import get_current_role, get_current_user_id
from core.database import pool
from services.graph_service import GraphService

router = APIRouter()


def _default_serializer(obj):
    from langchain_core.messages import BaseMessage

    if isinstance(obj, BaseMessage):
        return obj.dict()
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        return obj.model_dump()
    if hasattr(obj, "dict") and callable(obj.dict):
        return obj.dict()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def orjson_dumps(obj):
    return orjson.dumps(obj, default=_default_serializer).decode("utf-8")


async def run_bg_graph(thread_id: str, input_request: str, user_id: str):
    """Background task to run the graph."""
    try:
        graph = await GraphService.get_instance().get_graph()
        config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}
        initial_state = {"input_request": input_request}
        await graph.ainvoke(initial_state, config=config)
    except Exception as e:
        print(f"Background Job Error (Thread {thread_id}): {e}")


@router.post("/jobs", status_code=202)
async def create_job(
    input_request: str = Query(..., description="The input request for the agent"),
    background_tasks: BackgroundTasks = None,
    thread_id: str = "default",
    role: str = Depends(get_current_role),
    user_id: str = Depends(get_current_user_id),
):
    """
    Asynchronous Job Submission.
    Spawns a background task to run the agent workflow.
    Requires at least USER role.
    """
    valid_roles = ["USER", "EDITOR", "ADMIN", "ARCHITECT"]
    if role not in valid_roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions to execute jobs.")

    # Save conversation metadata immediately
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # Truncate title
                title = input_request[:50] + "..." if len(input_request) > 50 else input_request
                await cur.execute(
                    "INSERT INTO conversations (thread_id, title, created_at, updated_at) VALUES (%s, %s, NOW(), NOW()) ON CONFLICT (thread_id) DO NOTHING",
                    (thread_id, title),
                )
            await conn.commit()
    except Exception as e:
        print(f"Failed to save conversation: {e}")

    background_tasks.add_task(run_bg_graph, thread_id, input_request, user_id)

    return {
        "job_id": thread_id,
        "status": "queued",
        "message": f"Job accepted. Connect to /stream?thread_id={thread_id} for updates.",
    }


@router.post("/invoke", deprecated=True)
async def invoke(
    input_request: str = Query(...),
    background_tasks: BackgroundTasks = None,
    thread_id: str = "default",
    role: str = Depends(get_current_role),
):
    """
    Deprecated: Use POST /jobs instead.
    """
    return await create_job(
        input_request=input_request, background_tasks=background_tasks, thread_id=thread_id, role=role
    )


@router.post("/resume/{thread_id}")
async def resume(thread_id: str, feedback: str = None):
    """Resume execution after interrupt."""
    graph = await GraphService.get_instance().get_graph()

    config = {"configurable": {"thread_id": thread_id}}

    command = Command(resume=feedback) if feedback else None

    result = await graph.ainvoke(command, config=config)
    return result


@router.get("/stream")
async def stream(
    input_request: Optional[str] = None, thread_id: str = "default", resume_feedback: Optional[str] = None
):
    """
    Stream events via SSE.
    If 'resume_feedback' is provided, we treat this as a resume call.
    Otherwise 'input_request' is required to start a new run.
    """
    graph = await GraphService.get_instance().get_graph()

    config = {"configurable": {"thread_id": thread_id}}

    if resume_feedback is not None:
        # Resuming
        input_data = Command(resume=resume_feedback)
    elif input_request:
        # New Run
        input_data = {"input_request": input_request}

        # Save conversation metadata
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    title = input_request[:50] + "..." if len(input_request) > 50 else input_request
                    await cur.execute(
                        "INSERT INTO conversations (thread_id, title, created_at, updated_at) VALUES (%s, %s, NOW(), NOW()) ON CONFLICT (thread_id) DO NOTHING",
                        (thread_id, title),
                    )
                await conn.commit()
        except Exception as e:
            print(f"Failed to save conversation: {e}")
            pass
    else:
        input_data = None

    async def event_generator():
        try:
            # Check current state to get "HEAD" before we start running
            initial_state = await graph.aget_state(config)
            latest_checkpoint_id = None
            if initial_state and initial_state.config:
                latest_checkpoint_id = initial_state.config["configurable"].get("checkpoint_id")

            # Optimization: Instantiate Registry ONCE
            from brain.registry import AgentRegistry
            registry = AgentRegistry()
            # Cache the valid node names
            dynamic_agents = [agent.name for agent in registry.get_all()]
            valid_nodes = [
                "preprocess",
                "router",
                "supervisor",
                "tool_planning",
                "tool_execution",
                "qa",
            ] + dynamic_agents

            # Using astream_events for granular updates
            async for event in graph.astream_events(input_data, config=config, version="v2"):
                kind = event["event"]

                # 1. Token Streaming
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        metadata = event.get("metadata", {})
                        node = metadata.get("langgraph_node", "")
                        
                        # Fallback if node is missing (often true for CrewAI internal chains)
                        # We try to infer from the last known active node if we are in a node execution context
                        # But strictly, we should just report what we have.
                        
                        payload = orjson_dumps({"type": "token", "content": content, "node": node})
                        yield f"data: {payload}\n\n"

                # 2. Node Transitions
                elif kind == "on_chain_start":
                    node_name = event["name"]

                    if node_name in valid_nodes:
                        input_data_node = event["data"].get("input")
                        payload = {
                            "type": "node_start",
                            "node": node_name,
                            "thread_id": thread_id,  # Pass back thread_id as trace_id
                        }
                        if input_data_node:
                            payload["input"] = input_data_node

                        if latest_checkpoint_id:
                            payload["parent_checkpoint_id"] = latest_checkpoint_id

                        yield f"data: {orjson_dumps(payload)}\n\n"

                # 3. Node Completion
                elif kind == "on_chain_end":
                    node_name = event["name"]

                    if node_name in valid_nodes:
                        payload_dict = {"type": "node_end", "node": node_name}

                        output = event["data"].get("output")
                        if output:
                            payload_dict["output"] = output

                        yield f"data: {orjson_dumps(payload_dict)}\n\n"
                        
                        # We only fetch state if we really need the new checkpoint
                        # This avoids the expensive DB call per node-end
                        # But we need the checkpoint ID for the frontend to track history correctly.
                        # Optimization: Only do this for major nodes or try to parse checkpoint from event metadata if available.
                        # For now, we keep it but acknowledge the cost.

                        current_state = await graph.aget_state(config)
                        if current_state:
                            cid = current_state.config["configurable"]["checkpoint_id"]
                            pid = None
                            if current_state.parent_config:
                                pid = current_state.parent_config["configurable"].get("checkpoint_id")

                            latest_checkpoint_id = cid

                            cp_payload = {
                                "type": "checkpoint",
                                "node": node_name,
                                "checkpoint_id": cid,
                                "parent_checkpoint_id": pid,
                            }
                            yield f"data: {orjson_dumps(cp_payload)}\n\n"

            # Check if interrupted
            state = await graph.aget_state(config)
            if state.next:
                tool_call = state.values.get("tool_call")
                payload_dict = {"type": "interrupt", "next": state.next}
                if tool_call:
                    payload_dict["tool_call"] = tool_call

                if "qa" in state.next:
                    qa_preview = {
                        "context": state.values.get("context", ""),
                        "results": state.values.get("results", []),
                        "input_request": state.values.get("input_request", ""),
                    }
                    payload_dict["qa_preview"] = qa_preview

                payload = orjson_dumps(payload_dict)
                yield f"data: {payload}\n\n"
            else:
                yield "data: [DONE]\n\n"

        except Exception as e:
            print(f"Stream Error: {e}")
            yield f"data: {orjson_dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
