import zlib
from datetime import datetime, timezone
from typing import List, Optional

from dateutil import parser
from fastapi import APIRouter

from brain.logger import app_logger
from core.database import pool
from models.conversations import Conversation
from models.history import StepLogResponse
from services.graph_service import GraphService

router = APIRouter()


@router.get("/{thread_id}/topology")
async def get_checkpoints_topology(thread_id: str):
    """
    Retrieve pure topological structure of the graph execution.
    """
    graph = await GraphService.get_instance().get_graph()
    config = {"configurable": {"thread_id": thread_id}}

    raw_checkpoints = []
    try:
        async for state in graph.aget_state_history(config):
            if not state.created_at:
                continue
            raw_checkpoints.append(state)
    except Exception:
        return []

    cp_map = {state.config["configurable"]["checkpoint_id"]: state for state in raw_checkpoints}

    topology = []

    for state in raw_checkpoints:
        cid = state.config["configurable"]["checkpoint_id"]
        pid = state.parent_config["configurable"].get("checkpoint_id") if state.parent_config else None
        parallel_nodes = None

        node_name = "unknown"
        if state.metadata:
            node_name = state.metadata.get("langgraph_node", "unknown")

        if node_name == "unknown" and pid and pid in cp_map:
            parent_state = cp_map[pid]
            if parent_state.next:
                candidates = parent_state.next
                if len(candidates) == 1:
                    node_name = candidates[0]
                else:
                    writes = state.metadata.get("writes")
                    parallel_nodes = []
                    if writes and isinstance(writes, dict):
                        matches = [k for k in writes.keys() if k in candidates]
                        if len(matches) == 1:
                            node_name = matches[0]
                        elif len(matches) > 1:
                            node_name = ", ".join(matches)
                            parallel_nodes = matches

                    if node_name == "unknown":
                        node_name = ", ".join(candidates)
                        parallel_nodes = candidates

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


@router.get("/{thread_id}/steps", response_model=List[StepLogResponse])
async def get_step_history(thread_id: str):
    """Retrieve execution history for a specific thread."""
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

    all_checkpoints.sort(key=lambda x: parse_time(x.created_at).timestamp())

    cp_map = {}
    cp_node_map = {}

    for cp in all_checkpoints:
        cid = cp.config["configurable"]["checkpoint_id"]
        pid = None
        if cp.parent_config:
            pid = cp.parent_config["configurable"].get("checkpoint_id")
        cp_map[cid] = pid

        node_name = "unknown"
        if cp.metadata:
            node_name = cp.metadata.get("langgraph_node", "unknown")
        cp_node_map[cid] = node_name

    final_logs = []
    logs_by_cp = {}
    for log in logs:
        if log.checkpoint_id:
            if log.checkpoint_id not in logs_by_cp:
                logs_by_cp[log.checkpoint_id] = []
            logs_by_cp[log.checkpoint_id].append(log)

    from brain.registry import AgentRegistry

    registry = AgentRegistry()
    dynamic_agents = [agent.name for agent in registry.get_all()]
    valid_nodes = set(["preprocess", "supervisor", "tool_planning", "tool_execution", "qa"] + dynamic_agents)

    for cp in all_checkpoints:
        cid = cp.config["configurable"]["checkpoint_id"]
        pid = cp_map.get(cid)
        node_name = cp_node_map.get(cid)

        if node_name not in valid_nodes:
            continue

        timestamp = parse_time(cp.created_at)
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

        if cid in logs_by_cp:
            for log in logs_by_cp[cid]:
                log.parent_checkpoint_id = pid
                final_logs.append(log)

    for log in logs:
        if not log.checkpoint_id:
            final_logs.append(log)

    final_logs.sort(key=lambda x: parse_time(x.created_at).timestamp())
    return final_logs


@router.delete("/{thread_id}")
async def delete_conversation(thread_id: str):
    """Delete a conversation and its history."""
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM step_logs WHERE thread_id = %s", (thread_id,))
            await cur.execute("DELETE FROM conversations WHERE thread_id = %s", (thread_id,))
            return {"status": "success", "message": f"Conversation {thread_id} deleted"}


@router.get("/conversations", response_model=List[Conversation])
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


@router.get("/{thread_id}/checkpoints")
async def get_checkpoints(thread_id: str):
    """Retrieve checkpoints for time travel."""
    graph = await GraphService.get_instance().get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    checkpoints = []

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


@router.post("/fork")
async def fork_conversation(
    thread_id: str,
    checkpoint_id: str,
    new_input: Optional[str] = None,
    reset_to_step: Optional[str] = None,
):
    """
    Fork conversation from a specific checkpoint.
    """
    graph = await GraphService.get_instance().get_graph()
    config = {"configurable": {"thread_id": thread_id, "checkpoint_id": checkpoint_id}}

    target_checkpoint = await graph.aget_state(config)
    if not target_checkpoint:
        return {"error": "Checkpoint not found"}

    update_values = {}
    if new_input:
        original_input = target_checkpoint.values.get("input_request", "")
        if original_input:
            combined_input = f"{original_input}\n\n[Additional Context for Rerun]:\n{new_input}"
        else:
            combined_input = new_input
        update_values["input_request"] = combined_input

    if reset_to_step:
        update_values["next_step"] = [reset_to_step]

    try:
        await graph.aupdate_state(config, update_values)
    except Exception as e:
        app_logger.error(f"Fork failed: {e}")

    return {
        "status": "forked",
        "message": f"Forked conversation from checkpoint {checkpoint_id}",
    }
