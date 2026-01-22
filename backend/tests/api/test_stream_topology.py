from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from expects import contain, equal, expect
from httpx import AsyncClient

# Re-using fixtures pattern from test_main.py, but might need slight adjustments for stream


@pytest.fixture
def mock_graph_service():
    """Mock the GraphService singleton."""
    with (
        patch("api.v1.endpoints.execution.GraphService") as MockServiceExec,
        patch("api.v1.endpoints.history.GraphService") as MockServiceHist,
    ):
        mock_instance = MockServiceExec.get_instance.return_value
        mock_graph = AsyncMock()
        mock_instance.get_graph = AsyncMock(return_value=mock_graph)

        # Ensure history uses same mock
        MockServiceHist.get_instance.return_value = mock_instance

        yield mock_instance, mock_graph


@pytest.mark.asyncio
async def test_stream_new_run(client: AsyncClient, mock_graph_service, db_pool_mock, mock_user_headers):
    _, mock_graph = mock_graph_service

    class Chunk:
        content = "Hello"

    # Mock astream_events
    # It yields dictionaries.
    async def event_generator(*args, **kwargs):
        # 1. Token
        yield {
            "event": "on_chat_model_stream",
            "data": {"chunk": Chunk()},
            "metadata": {"langgraph_node": "agent_node"},
        }
        # 2. Node Start
        yield {
            "event": "on_chain_start",
            "name": "supervisor",
            "data": {"input": "User Input"},
        }
        # 3. Node End
        yield {
            "event": "on_chain_end",
            "name": "supervisor",
            "data": {"output": "Agent Output"},
        }

    mock_graph.astream_events = event_generator
    mock_state = MagicMock(config={"configurable": {"checkpoint_id": "cp1"}})
    mock_state.parent_config = None
    mock_state.next = None
    mock_graph.aget_state.return_value = mock_state

    async with client.stream("GET", "/stream?input_request=Test", headers=mock_user_headers) as response:
        expect(response.status_code).to(equal(200))
        lines = []
        async for line in response.aiter_lines():
            if line.strip():
                lines.append(line)

        # distinct events:
        # data: {"type": "token", ...}
        # data: {"type": "node_start", ...}
        # data: {"type": "node_end", ...}
        # data: [DONE]

    # Verify we got some data
    expect(len(lines)).to(equal(5))
    expect(lines[-1]).to(equal("data: [DONE]"))
    expect(lines[0]).to(contain('"type":"token"'))


@pytest.mark.asyncio
async def test_stream_resume(client: AsyncClient, mock_graph_service, mock_user_headers):
    _, mock_graph = mock_graph_service

    async def event_generator(*args, **kwargs):
        yield {"event": "on_chain_end", "name": "supervisor", "data": {"output": "Resumed"}}

    mock_graph.astream_events = event_generator
    mock_state = MagicMock(config={"configurable": {"checkpoint_id": "cp2"}})
    mock_state.parent_config = None
    mock_state.next = None
    mock_graph.aget_state.return_value = mock_state

    async with client.stream("GET", "/stream?thread_id=t1&resume_feedback=Go", headers=mock_user_headers) as response:
        expect(response.status_code).to(equal(200))
        lines = [line async for line in response.aiter_lines() if line]

    expect(lines[0]).to(contain('"type":"node_end"'))


@pytest.mark.asyncio
async def test_stream_interrupt(client: AsyncClient, mock_graph_service, mock_user_headers):
    _, mock_graph = mock_graph_service
    mock_graph.astream_events = AsyncMock(return_value=[])  # No events needed for this test part really

    # But astream_events is an async generator, so returning empty list isn't enough, needs to be generator or iter
    async def empty_gen(*args, **kwargs):
        if False:
            yield

    mock_graph.astream_events = empty_gen

    # Mock state with interrupt
    mock_state = MagicMock()
    mock_state.config = {"configurable": {"checkpoint_id": "cp1"}}
    mock_state.parent_config = None
    mock_state.next = ("tool_node",)
    mock_state.values = {"tool_call": "call_1", "context": "ctx"}
    mock_graph.aget_state.return_value = mock_state

    async with client.stream("GET", "/stream?thread_id=t1", headers=mock_user_headers) as response:
        lines = [line async for line in response.aiter_lines() if line]

    # Should see interrupt message
    expect(lines[0]).to(contain('"type":"interrupt"'))


@pytest.mark.asyncio
async def test_resume_post(client: AsyncClient, mock_graph_service, mock_user_headers):
    _, mock_graph = mock_graph_service
    mock_graph.ainvoke.return_value = {"output": "Resumed"}

    response = await client.post("/resume/t1", params={"feedback": "Go"}, headers=mock_user_headers)
    expect(response.status_code).to(equal(200))
    expect(mock_graph.ainvoke.called).to(equal(True))


@pytest.mark.asyncio
async def test_get_checkpoints_topology(client: AsyncClient, mock_graph_service, mock_user_headers):
    _, mock_graph = mock_graph_service
    now = datetime.now(timezone.utc)

    # Mock history
    state1 = MagicMock()
    state1.config = {"configurable": {"checkpoint_id": "cp1"}}
    state1.parent_config = None
    state1.metadata = {"langgraph_node": "__start__"}
    state1.created_at = now.isoformat()
    state1.next = ("node_a",)

    state2 = MagicMock()
    state2.config = {"configurable": {"checkpoint_id": "cp2"}}
    state2.parent_config = {"configurable": {"checkpoint_id": "cp1"}}
    state2.metadata = {"langgraph_node": "node_a"}
    state2.created_at = now.isoformat()
    state2.next = ()

    # infer topology logic relies on iterating history
    async def history_gen(*args, **kwargs):
        yield state1
        yield state2

    mock_graph.aget_state_history = history_gen

    response = await client.get("/history/t1/topology", headers=mock_user_headers)
    expect(response.status_code).to(equal(200))
    data = response.json()
    expect(len(data)).to(equal(2))
    expect(data[0]["id"]).to(equal("cp1"))
    expect(data[1]["parent_id"]).to(equal("cp1"))


@pytest.mark.asyncio
async def test_get_checkpoints(client: AsyncClient, mock_graph_service, mock_user_headers):
    _, mock_graph = mock_graph_service
    now = datetime.now(timezone.utc)

    state1 = MagicMock()
    state1.config = {"configurable": {"checkpoint_id": "cp1"}}
    state1.created_at = now.isoformat()
    state1.next = ("node_a",)
    state1.metadata = {}
    state1.tasks = []

    async def history_gen(*args, **kwargs):
        yield state1

    mock_graph.aget_state_history = history_gen

    response = await client.get("/history/t1/checkpoints", headers=mock_user_headers)
    expect(response.status_code).to(equal(200))
    data = response.json()
    expect(len(data)).to(equal(1))
    expect(data[0]["id"]).to(equal("cp1"))
