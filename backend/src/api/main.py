import zlib
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List

import orjson
from dateutil import parser
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import BaseMessage
from langgraph.types import Command

from src.api.mcp import router as mcp_router
from src.api.v1.endpoints.agents import router as agents_router
from src.api.v1.endpoints.config_endpoints import router as config_router
from src.api.v1.endpoints.files import router as files_router
from src.api.v1.endpoints.infrastructure import router as infra_router
from src.core.database import pool
from src.models.conversations import Conversation
from src.models.history import StepLogResponse
from src.services.graph_service import GraphService


def _default_serializer(obj):
    if isinstance(obj, BaseMessage):
        return obj.dict()
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        return obj.model_dump()
    if hasattr(obj, "dict") and callable(obj.dict):
        return obj.dict()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def orjson_dumps(obj):
    return orjson.dumps(obj, default=_default_serializer).decode("utf-8")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Open DB pool
    await pool.open()

    # Initial Graph Load
    await GraphService.get_instance().reload_graph()

    yield

    # Shutdown: Close DB pool
    await pool.close()


app = FastAPI(title="LangGraph-CrewAI Bridge", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mcp_router)
app.include_router(agents_router, prefix="/agents", tags=["agents"])
app.include_router(config_router, prefix="/configurations", tags=["configurations"])
app.include_router(infra_router, prefix="/infrastructure", tags=["infrastructure"])
app.include_router(files_router, prefix="/files", tags=["files"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/invoke")
async def invoke(input_request: str, thread_id: str = "default"):
    """Synchronous invocation."""
    graph = await GraphService.get_instance().get_graph()

    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {"input_request": input_request}

    # We use ainvoke; if it hits the interrupt, it will stop partially.
    result = await graph.ainvoke(initial_state, config=config)
    return result


@app.post("/resume/{thread_id}")
async def resume(thread_id: str, feedback: str = None):
    """Resume execution after interrupt."""
    graph = await GraphService.get_instance().get_graph()

    config = {"configurable": {"thread_id": thread_id}}

    command = Command(resume=feedback) if feedback else None

    result = await graph.ainvoke(command, config=config)
    return result


@app.get("/stream")
async def stream(input_request: str = None, thread_id: str = "default", resume_feedback: str = None):
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
                    # Truncate title
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

            # Using astream_events for granular updates
            async for event in graph.astream_events(input_data, config=config, version="v2"):
                kind = event["event"]

                # 1. Token Streaming
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        # Extract node name from metadata to support parallel streaming
                        metadata = event.get("metadata", {})
                        node = metadata.get("langgraph_node", "")

                        payload = orjson_dumps({"type": "token", "content": content, "node": node})
                        yield f"data: {payload}\n\n"

                # 2. Node Transitions
                elif kind == "on_chain_start":
                    node_name = event["name"]

                    # Get dynamic agents
                    from src.brain.registry import AgentRegistry

                    registry = AgentRegistry()
                    dynamic_agents = [agent.name for agent in registry.get_all()]

                    valid_nodes = [
                        "preprocess",
                        "router",
                        "supervisor",
                        "tool_planning",
                        "tool_execution",
                        "qa",
                    ] + dynamic_agents

                    if node_name in valid_nodes:
                        # Capture input if available
                        input_data_node = event["data"].get("input")
                        payload = {"type": "node_start", "node": node_name}
                        if input_data_node:
                            payload["input"] = input_data_node

                        # Provide parent context (This is a guess during stream, backend clarifies later)
                        if latest_checkpoint_id:
                            payload["parent_checkpoint_id"] = latest_checkpoint_id

                        yield f"data: {orjson_dumps(payload)}\n\n"

                # 3. Node Completion
                elif kind == "on_chain_end":
                    node_name = event["name"]

                    # Same valid nodes check
                    from src.brain.registry import AgentRegistry

                    registry = AgentRegistry()
                    dynamic_agents = [agent.name for agent in registry.get_all()]

                    valid_nodes = [
                        "preprocess",
                        "router",
                        "supervisor",
                        "tool_planning",
                        "tool_execution",
                        "qa",
                    ] + dynamic_agents

                    if node_name in valid_nodes:
                        payload_dict = {"type": "node_end", "node": node_name}

                        # Capture output for ALL nodes to show in graph
                        output = event["data"].get("output")
                        if output:
                            payload_dict["output"] = output

                        yield f"data: {orjson_dumps(payload_dict)}\n\n"

                        # Check state to get new checkpoint ID
                        current_state = await graph.aget_state(config)
                        if current_state:
                            cid = current_state.config["configurable"]["checkpoint_id"]
                            pid = None
                            if current_state.parent_config:
                                pid = current_state.parent_config["configurable"].get("checkpoint_id")

                            # Update our local tracker
                            latest_checkpoint_id = cid

                            # Emit a dedicated 'checkpoint' event
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
                # If there are next steps but execution stopped, it's likely an interrupt
                tool_call = state.values.get("tool_call")
                payload_dict = {"type": "interrupt", "next": state.next}
                if tool_call:
                    payload_dict["tool_call"] = tool_call

                # If QA is next, provide preview of what it will analyze
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


@app.get("/history/{thread_id}/topology")
async def get_checkpoints_topology(thread_id: str):
    """
    Retrieve pure topological structure of the graph execution.
    This serves as the robust skeleton for the frontend visualizer.
    """
    graph = await GraphService.get_instance().get_graph()
    config = {"configurable": {"thread_id": thread_id}}

    # We need to collect all checkpoints first to map parents -> children -> inferred names
    raw_checkpoints = []
    try:
        async for state in graph.aget_state_history(config):
            if not state.created_at:
                continue
            raw_checkpoints.append(state)
    except Exception:
        return []

    # Sort by time asc for easier processing (though we can map by ID)
    # Actually, aget_state_history returns desc usually.

    # Map CheckpointID -> State
    cp_map = {state.config["configurable"]["checkpoint_id"]: state for state in raw_checkpoints}

    topology = []

    for state in raw_checkpoints:
        cid = state.config["configurable"]["checkpoint_id"]
        pid = state.parent_config["configurable"].get("checkpoint_id") if state.parent_config else None
        parallel_nodes = None

        # Determine which node produced this checkpoint
        # 1. Try explicit metadata
        node_name = "unknown"
        if state.metadata:
            # Some versions use 'langgraph_node'
            node_name = state.metadata.get("langgraph_node", "unknown")

            # Fallback: if 'writes' has a key that matches a known node?
            # writes = state.metadata.get("writes")
            # if node_name == "unknown" and writes:
            #    pass

        # 2. Strong Fallback: Look at Parent's 'next'
        # If Parent says "Next is X", then THIS checkpoint is likely the result of X.
        if node_name == "unknown" and pid and pid in cp_map:
            parent_state = cp_map[pid]
            if parent_state.next:
                # state.next is tuple of strings
                candidates = parent_state.next
                if len(candidates) == 1:
                    node_name = candidates[0]
                else:
                    # Parallel execution: CP is result of ONE of the parallel nodes.
                    # We check 'writes' in metadata to disambiguate.
                    writes = state.metadata.get("writes")
                    parallel_nodes = []

                    if writes and isinstance(writes, dict):
                        # Find intersection between writes keys and candidates
                        matches = [k for k in writes.keys() if k in candidates]
                        if len(matches) == 1:
                            node_name = matches[0]
                        elif len(matches) > 1:
                            node_name = ", ".join(matches)
                            parallel_nodes = matches

                    # Fallback: if writes are missing (common in some configs), assume all candidates ran (merged)
                    if node_name == "unknown":
                        node_name = ", ".join(candidates)
                        parallel_nodes = candidates

        # 3. Special Case: __start__
        if node_name == "unknown" and not pid:
            node_name = "__start__"

        topology.append(
            {
                "id": cid,
                "parent_id": pid,
                "node": node_name,
                "parallel_nodes": parallel_nodes,
                "created_at": state.created_at,
                "metadata": state.metadata,
            }
        )

    return topology


@app.get("/history/{thread_id}/steps", response_model=List[StepLogResponse])
async def get_step_history(thread_id: str):
    """Retrieve execution history for a specific thread."""

    # 1. Fetch Logs from DB
    logs = []
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, thread_id, step_name, log_type, content, created_at, checkpoint_id FROM step_logs WHERE thread_id = %s ORDER BY created_at ASC",
                (thread_id,),
            )
            rows = await cur.fetchall()
            logs = [
                StepLogResponse(
                    id=row[0],
                    thread_id=row[1],
                    step_name=row[2],
                    log_type=row[3],
                    content=row[4],
                    created_at=row[5],
                    checkpoint_id=row[6],
                )
                for row in rows
            ]

    graph = await GraphService.get_instance().get_graph()

    # 2. Fetch Checkpoints from LangGraph
    # Structure: Map Checkpoint ID -> Parent Checkpoint ID
    config = {"configurable": {"thread_id": thread_id}}
    all_checkpoints = []
    try:
        async for state in graph.aget_state_history(config):
            if state.created_at:
                all_checkpoints.append(state)
    except Exception:
        pass

    def parse_time(t):
        if isinstance(t, str):
            try:
                dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
            except ValueError:
                dt = parser.parse(t)
        else:
            dt = t
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    # Sort checks by time
    all_checkpoints.sort(key=lambda x: parse_time(x.created_at).timestamp())

    # Build Map
    cp_map = {}  # ID -> ParentID
    cp_node_map = {}  # ID -> NodeName

    for cp in all_checkpoints:
        cid = cp.config["configurable"]["checkpoint_id"]
        pid = None
        if cp.parent_config:
            pid = cp.parent_config["configurable"].get("checkpoint_id")
        cp_map[cid] = pid

        # Identify node name
        node_name = "unknown"
        if cp.metadata:
            node_name = cp.metadata.get("langgraph_node", "unknown")
        cp_node_map[cid] = node_name

    # 3. Enrich Logs with strict Parent IDs
    final_logs = []

    # We primarily iterate the checkpoints to ensure topological correctness
    # Then we attach the log content to them.

    # Index real logs by (checkpoint_id, step_name) or just (checkpoint_id)
    logs_by_cp = {}
    for log in logs:
        if log.checkpoint_id:
            if log.checkpoint_id not in logs_by_cp:
                logs_by_cp[log.checkpoint_id] = []
            logs_by_cp[log.checkpoint_id].append(log)

    # List of known agent/node names to filter noise
    from src.brain.registry import AgentRegistry

    registry = AgentRegistry()
    dynamic_agents = [agent.name for agent in registry.get_all()]
    valid_nodes = set(
        [
            "preprocess",
            "supervisor",
            "tool_planning",
            "tool_execution",
            "qa",
        ]
        + dynamic_agents
    )

    for cp in all_checkpoints:
        cid = cp.config["configurable"]["checkpoint_id"]
        pid = cp_map.get(cid)
        node_name = cp_node_map.get(cid)

        # Determine if this checkpoint represents a valid node execution
        if node_name not in valid_nodes:
            continue

        # Create a "Node Start" synthetic log if one doesn't exist
        # This guarantees the graph node existence even if no content was logged

        timestamp = parse_time(cp.created_at)

        # Add "Start" marker
        # Generate stable ID
        id_key = f"{thread_id}_{cid}_{node_name}_start".encode("utf-8")
        synth_id = -abs(zlib.adler32(id_key))

        final_logs.append(
            StepLogResponse(
                id=synth_id,
                thread_id=thread_id,
                step_name=node_name,
                log_type="node_start",
                content=f"Activating Node: {node_name.upper()}",
                created_at=timestamp,
                checkpoint_id=cid,
                parent_checkpoint_id=pid,
            )
        )

        # Add real content logs associated with this checkpoint
        if cid in logs_by_cp:
            for log in logs_by_cp[cid]:
                # Ensure parent pointer is correct
                log.parent_checkpoint_id = pid
                final_logs.append(log)

    # Add logs that have NO checkpoint_id (legacy or error) -> Append to end?
    # Or try to map by time? For now, we append them but they might float.
    # Ideally we want to avoid loose logs.
    for log in logs:
        if not log.checkpoint_id:
            # Try to find nearest checkpoint?
            # For strict time travel, we might ignore them or put them at root.
            # Let's include them for debug purposes.
            final_logs.append(log)

    final_logs.sort(key=lambda x: parse_time(x.created_at).timestamp())

    return final_logs


@app.delete("/history/{thread_id}")
async def delete_conversation(thread_id: str):
    """Delete a conversation and its history."""
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            # Delete logs
            await cur.execute("DELETE FROM step_logs WHERE thread_id = %s", (thread_id,))
            # Delete conversation metadata
            await cur.execute("DELETE FROM conversations WHERE thread_id = %s", (thread_id,))
            return {"status": "success", "message": f"Conversation {thread_id} deleted"}


@app.get("/history/conversations", response_model=List[Conversation])
async def list_conversations():
    """List all conversations ordered by last update."""
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, thread_id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
            )
            rows = await cur.fetchall()
            return [
                Conversation(
                    id=row[0],
                    thread_id=row[1],
                    title=row[2],
                    created_at=row[3],
                    updated_at=row[4],
                )
                for row in rows
            ]


@app.get("/agents")
async def get_agents():
    """Get list of registered agents for UI visualization."""
    from src.brain.registry import AgentRegistry

    registry = AgentRegistry()
    agents = registry.get_all()

    return [
        {
            "id": agent.name,
            "label": f"{agent.display_name} Agent",
            "role": agent.agent.role,
            "description": agent.description,
        }
        for agent in agents
    ]


@app.get("/history/{thread_id}/checkpoints")
async def get_checkpoints(thread_id: str):
    """Retrieve checkpoints for time travel."""
    graph = await GraphService.get_instance().get_graph()

    config = {"configurable": {"thread_id": thread_id}}
    checkpoints = []

    # Iterate over history
    async for state in graph.aget_state_history(config):
        if not state.created_at:
            continue

        checkpoints.append(
            {
                "id": state.config["configurable"]["checkpoint_id"],
                "created_at": state.created_at,
                "next": state.next,
                "metadata": state.metadata,
                "tasks": [t.name for t in state.tasks] if state.tasks else [],
            }
        )

    return checkpoints


@app.post("/fork")
async def fork_conversation(
    thread_id: str,
    checkpoint_id: str,
    new_input: str = None,
    reset_to_step: str = None,
):
    """
    Fork conversation from a specific checkpoint.
    This effectively "rewinds" the state to that point.
    """
    graph = await GraphService.get_instance().get_graph()

    config = {"configurable": {"thread_id": thread_id, "checkpoint_id": checkpoint_id}}

    # 1. Fetch Checkpoint & Timestamp
    target_checkpoint = await graph.aget_state(config)
    if not target_checkpoint:
        return {"error": "Checkpoint not found"}

    cutoff_time = target_checkpoint.created_at

    # Timezone Handling
    if cutoff_time:
        if isinstance(cutoff_time, str):
            try:
                cutoff_time = datetime.fromisoformat(cutoff_time.replace("Z", "+00:00"))
            except ValueError:
                cutoff_time = parser.parse(cutoff_time)
        if cutoff_time.tzinfo is None:
            cutoff_time = cutoff_time.replace(tzinfo=timezone.utc)

    # 2. Perform the Fork / Update State
    # We update the state AT the target checkpoint. This automatically creates a new branch (checkpoint)
    # in LangGraph's history, effectively "forking" the timeline.

    update_values = {}
    if new_input:
        # Get original input from the checkpoint state to preserve context
        original_input = target_checkpoint.values.get("input_request", "")

        # Combine new input with original instead of replacing
        if original_input:
            # Append new input to original with clear formatting
            combined_input = f"{original_input}\n\n[Additional Context for Rerun]:\n{new_input}"
        else:
            # If no original input exists, just use the new input
            combined_input = new_input

        update_values["input_request"] = combined_input

    # If we want to force execution to start at a specific node (e.g. 'research_agent') instead of
    # the natural next step, we can manipulate the state or 'as_node'.
    # However, usually we just want to update input and let it flow.
    # If reset_to_step is provided, we can try to hint the router or next step.
    if reset_to_step:
        update_values["next_step"] = [reset_to_step]

    # Determine 'as_node'. If we are modifying the initial input, we act as 'user' or 'root'.
    # If we are rewinding to a middle step, we act as the node that produced the checkpoint?
    # Actually, update_state usually takes 'as_node' to impersonate a write.
    # Safe default is often 'supervisor' or the node itself if it's an interrupt.

    # We'll use the metadata from the checkpoint to see who "owned" it, or default to internal
    as_node = "supervisor"
    # Try to find who wrote what to determine ownership if needed
    # But for input updates, 'interrupt' owner is usually best.

    try:
        await graph.aupdate_state(config, update_values)  # , as_node=as_node)
    except Exception as e:
        # Fallback: sometimes we can't write as a specific node if it wasn't the last writer.
        # Try writing as 'supervisor' generic or just let it fail to debug.
        print(f"Fork failed as {as_node}, trying default. Error: {e}")
        # await graph.aupdate_state(config, update_values)

    return {
        "status": "forked",
        "message": f"Forked conversation from checkpoint {checkpoint_id}",
    }
