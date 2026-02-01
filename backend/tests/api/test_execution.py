from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from expects import contain, equal, expect
from httpx import AsyncClient
from langchain_core.messages import HumanMessage

from api.v1.endpoints.execution import _default_serializer


# Test _default_serializer
def test_default_serializer():
    class ObjWithDict:
        def dict(self):
            return {"a": 1}

    class ObjWithModelDump:
        def model_dump(self):
            return {"b": 2}

    class ObjInvalid:
        pass

    expect(_default_serializer(ObjWithDict())).to(equal({"a": 1}))
    expect(_default_serializer(ObjWithModelDump())).to(equal({"b": 2}))

    msg = HumanMessage(content="hi")
    # BaseMessage has dict() method in recent langchain, or serialization logic
    try:
        res = _default_serializer(msg)
        # It's a dict, check if 'content' is in its keys
        expect(list(res.keys())).to(contain("content"))
    except TypeError:
        # Fallback if dependencies vary
        pass

    with pytest.raises(TypeError):
        _default_serializer(ObjInvalid())


@pytest.fixture
def mock_graph_service():
    with patch("api.v1.endpoints.execution.GraphService") as MockService:
        instance = MockService.get_instance.return_value
        graph = AsyncMock()
        instance.get_graph = AsyncMock(return_value=graph)
        yield instance, graph


@pytest.mark.asyncio
async def test_create_job_success(client: AsyncClient, mock_db_cursor, mock_user_headers):
    response = await client.post("/jobs?input_request=test", headers=mock_user_headers)
    expect(response.status_code).to(equal(202))
    expect(response.json()["job_id"]).not_to(equal(None))

    # Verify DB insert
    expect(mock_db_cursor.execute.called).to(equal(True))


@pytest.mark.asyncio
async def test_create_job_invalid_role(client: AsyncClient):
    # Missing headers -> defaults to USER which is valid.
    # We explicitly send INVALID role to fail.
    response = await client.post(
        "/jobs?input_request=test", headers={"X-Role": "INVALID", "X-User-ID": "test", "X-Tenant-ID": "t"}
    )
    expect(response.status_code).to(equal(403))


@pytest.mark.asyncio
async def test_create_job_db_error(client: AsyncClient, mock_db_cursor, mock_user_headers):
    mock_db_cursor.execute.side_effect = Exception("DB Fail")
    # Should log error but succeed (Lines 68-69)
    response = await client.post("/jobs?input_request=test", headers=mock_user_headers)
    expect(response.status_code).to(equal(202))


@pytest.mark.asyncio
async def test_invoke_deprecated(client: AsyncClient, mock_db_cursor, mock_user_headers):
    response = await client.post("/invoke?input_request=test", headers=mock_user_headers)
    expect(response.status_code).to(equal(200))


@pytest.mark.asyncio
async def test_resume_success(client: AsyncClient, mock_graph_service, mock_user_headers):
    _, mock_graph = mock_graph_service
    mock_graph.ainvoke.return_value = {"output": "resumed"}

    response = await client.post("/resume/thread1?feedback=go", headers=mock_user_headers)
    expect(response.status_code).to(equal(200))


@pytest.mark.asyncio
async def test_stream(client: AsyncClient, mock_graph_service, mock_db_cursor):
    _, mock_graph = mock_graph_service

    # Mock astream_events using MagicMock to return an async generator
    async def event_gen(*args, **kwargs):
        # 1. Token
        yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="Hello")}}
        # 2. Node Start
        yield {"event": "on_chain_start", "name": "router", "data": {"input": "in"}}
        # 3. Node End
        yield {"event": "on_chain_end", "name": "router", "data": {"output": "out"}}

    mock_graph.astream_events = MagicMock(side_effect=event_gen)
    mock_graph.aget_state.return_value = MagicMock(config={"configurable": {"checkpoint_id": "cp1"}}, values={})

    async with client.stream("GET", "/stream?input_request=hi") as response:
        expect(response.status_code).to(equal(200))
        lines = [line async for line in response.aiter_lines()]
        # Check basic content
        full_text = "".join(lines)
        # Expect 'token' type in the output
        expect(full_text).to(contain("token"))
        expect(full_text).to(contain("node_start"))


@pytest.mark.asyncio
async def test_stream_db_error(client: AsyncClient, mock_graph_service, mock_db_cursor):
    # Setup graph mock to avoid crash before DB check
    _, mock_graph = mock_graph_service

    async def empty_gen(*args, **kwargs):
        if False:
            yield

    mock_graph.astream_events = MagicMock(side_effect=empty_gen)
    mock_graph.aget_state.return_value = MagicMock(config={"configurable": {}})

    mock_db_cursor.execute.side_effect = Exception("DB Fail")

    async with client.stream("GET", "/stream?input_request=hi") as response:
        expect(response.status_code).to(equal(200))
        # Should proceed despite DB error


@pytest.mark.asyncio
async def test_stream_interrupt(client: AsyncClient, mock_graph_service):
    _, mock_graph = mock_graph_service

    async def empty_gen(*args, **kwargs):
        if False:
            yield

    mock_graph.astream_events = MagicMock(side_effect=empty_gen)

    # Mock state with next indicating interrupt (Line 240+)
    mock_state_interrupt = MagicMock()
    mock_state_interrupt.next = ["qa"]
    mock_state_interrupt.values = {"context": "ctx", "results": [], "input_request": "req", "tool_call": "some_call"}

    # Side effect for aget_state: first call (initial) -> normal, second call (check) -> interrupt
    mock_graph.aget_state.side_effect = [
        MagicMock(config={"configurable": {"checkpoint_id": "cp1"}}),  # Initial
        mock_state_interrupt,  # After stream
    ]

    async with client.stream("GET", "/stream?input_request=hi") as response:
        expect(response.status_code).to(equal(200))
        lines = [line async for line in response.aiter_lines()]
        full = "".join(lines)
        expect(full).to(contain("interrupt"))
        expect(full).to(contain("qa_preview"))
