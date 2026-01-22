from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from expects import contain, equal, expect
from httpx import AsyncClient


@pytest.fixture
def mock_graph_service():
    with patch("api.v1.endpoints.history.GraphService") as MockService:
        instance = MockService.get_instance.return_value
        graph = AsyncMock()
        instance.get_graph = AsyncMock(return_value=graph)
        yield instance, graph


@pytest.mark.asyncio
async def test_get_checkpoints_topology(client: AsyncClient, mock_graph_service):
    _, mock_graph = mock_graph_service

    # Create mock states
    # 1. Root state
    state1 = MagicMock()
    state1.config = {"configurable": {"checkpoint_id": "cp1"}}
    state1.parent_config = None
    state1.metadata = {"langgraph_node": "start_node"}
    state1.created_at = "2023-01-01T10:00:00Z"

    # 2. Child state
    state2 = MagicMock()
    state2.config = {"configurable": {"checkpoint_id": "cp2"}}
    state2.parent_config = {"configurable": {"checkpoint_id": "cp1"}}
    state2.metadata = {"langgraph_node": "node2"}
    state2.created_at = "2023-01-01T10:01:00Z"

    # 3. State with unknown node + parallel writes (Lines 45-63 coverage)
    state3 = MagicMock()
    state3.config = {"configurable": {"checkpoint_id": "cp3"}}
    state3.parent_config = {"configurable": {"checkpoint_id": "cp2"}}
    state3.metadata = {"langgraph_node": "unknown", "writes": {"parallel1": "val"}}
    state3.created_at = "2023-01-01T10:02:00Z"

    # Mock cp2 next to allow resolution
    state2.next = ["parallel1", "parallel2"]

    # 4. State with missing created_at (should be skipped) line 25
    state4 = MagicMock()
    state4.created_at = None

    async def history_gen(*args, **kwargs):
        yield state1
        yield state2
        yield state3
        yield state4

    mock_graph.aget_state_history = MagicMock(side_effect=history_gen)

    response = await client.get("/history/thread1/topology")
    expect(response.status_code).to(equal(200))
    topo = response.json()
    expect(len(topo)).to(equal(3))  # state4 skipped

    # Verify name resolution for cp3
    item3 = next(i for i in topo if i["id"] == "cp3")
    expect(item3["node"]).to(equal("parallel1"))


@pytest.mark.asyncio
async def test_get_checkpoints_topology_error(client: AsyncClient, mock_graph_service):
    _, mock_graph = mock_graph_service
    mock_graph.aget_state_history = MagicMock(side_effect=Exception("Graph Error"))

    response = await client.get("/history/thread1/topology")
    expect(response.status_code).to(equal(200))
    expect(response.json()).to(equal([]))


@pytest.mark.asyncio
async def test_get_step_history(client: AsyncClient, mock_graph_service, mock_db_cursor):
    _, mock_graph = mock_graph_service

    # DB Logs - Using Int IDs
    mock_db_cursor.fetchall.return_value = [
        (1, "thread1", "agent1", "text", "hi", datetime(2023, 1, 1, 10, 0, 0), "cp1"),
        (2, "thread1", "agent1", "text", "orphan", datetime(2023, 1, 1, 10, 5, 0), None),
    ]

    # Graph History
    state1 = MagicMock()
    state1.config = {"configurable": {"checkpoint_id": "cp1"}}
    state1.parent_config = None
    state1.metadata = {"langgraph_node": "agent1"}  # Valid node
    state1.created_at = "2023-01-01T10:00:00Z"

    async def history_gen(*args, **kwargs):
        yield state1

    mock_graph.aget_state_history = MagicMock(side_effect=history_gen)

    with patch("brain.registry.AgentRegistry") as MockRegistry:
        agent = MagicMock()
        agent.name = "agent1"
        MockRegistry.return_value.get_all.return_value = [agent]

        response = await client.get("/history/thread1/steps")
        expect(response.status_code).to(equal(200))
        steps = response.json()
        expect(len(steps)).to(equal(3))


@pytest.mark.asyncio
async def test_delete_conversation(client: AsyncClient, mock_db_cursor):
    response = await client.delete("/history/thread1")
    expect(response.status_code).to(equal(200))
    expect(mock_db_cursor.execute.call_count).to(equal(2))


@pytest.mark.asyncio
async def test_list_conversations(client: AsyncClient, mock_db_cursor):
    mock_db_cursor.fetchall.return_value = [(1, "t1", "Title", datetime.now(), datetime.now())]
    response = await client.get("/history/conversations")
    expect(response.status_code).to(equal(200))
    expect(len(response.json())).to(equal(1))


@pytest.mark.asyncio
async def test_fork_conversation(client: AsyncClient, mock_graph_service):
    _, mock_graph = mock_graph_service

    target = MagicMock()
    target.values = {"input_request": "original"}
    mock_graph.aget_state.return_value = target

    response = await client.post("/history/fork?thread_id=t1&checkpoint_id=cp1&new_input=new&reset_to_step=step1")
    expect(response.status_code).to(equal(200))

    args, _ = mock_graph.aupdate_state.call_args
    expect(args[1]["input_request"]).to(contain("original"))
    expect(args[1]["input_request"]).to(contain("new"))
    expect(args[1]["next_step"]).to(equal(["step1"]))


@pytest.mark.asyncio
async def test_fork_conversation_not_found(client: AsyncClient, mock_graph_service):
    _, mock_graph = mock_graph_service
    mock_graph.aget_state.return_value = None

    response = await client.post("/history/fork?thread_id=t1&checkpoint_id=cp1")
    expect(response.json()).to(equal({"error": "Checkpoint not found"}))
