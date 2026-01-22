from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from expects import be_a, contain, equal, expect, have_keys
from httpx import AsyncClient

# Mock data
agent1 = MagicMock()
agent1.name = "agent1"
agent1.display_name = "Agent One"
agent1.description = "Desc 1"
agent1.agent.role = "Role 1"

agent2 = MagicMock()
agent2.name = "agent2"
agent2.display_name = "Agent Two"
agent2.description = "Desc 2"
agent2.agent.role = "Role 2"

MOCK_AGENT_LIST = [agent1, agent2]


@pytest.fixture
def mock_graph_service():
    """Mock the GraphService singleton."""
    # Updated path: api.v1.endpoints.execution uses GraphService
    # But also api.v1.endpoints.history uses it.
    # It's safer to patch the class itself where it is imported or used.
    # Since we use `patch("api.v1.endpoints.execution.GraphService")` etc.
    # But GraphService is imported in both.
    # Ideally we mock `services.graph_service.GraphService` but that might be tricky with singleton get_instance.
    # Let's patch where it's used in the module under test execution.
    # But wait, we are testing the endpoint logic which calls GraphService.get_instance().

    # We will patch it in both execution and history modules for safety in this file
    # Or just patch the service method directly if possible.

    # Let's patch the one in execution for job tests
    with (
        patch("api.v1.endpoints.execution.GraphService") as MockServiceExec,
        patch("api.v1.endpoints.history.GraphService") as MockServiceHist,
    ):
        mock_instance = MockServiceExec.get_instance.return_value
        mock_graph = AsyncMock()
        mock_instance.get_graph = AsyncMock(return_value=mock_graph)
        mock_instance.reload_graph = AsyncMock()

        # Ensure history uses same mock
        MockServiceHist.get_instance.return_value = mock_instance

        yield mock_instance, mock_graph


@pytest.fixture
def mock_agent_registry():
    """Mock the AgentRegistry."""
    # Used in agents.py for /summary endpoint
    # Since agents.py imports AgentRegistry at top level, we must patch it directly there
    with patch("api.v1.endpoints.agents.AgentRegistry") as MockRegistry:
        mock_instance = MockRegistry.return_value
        mock_instance.get_all.return_value = MOCK_AGENT_LIST
        yield mock_instance


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health")
    expect(response.status_code).to(equal(200))
    expect(response.json()).to(equal({"status": "ok"}))


@pytest.mark.asyncio
async def test_create_job_success(client: AsyncClient, mock_graph_service, db_pool_mock, mock_user_headers):
    _, mock_graph = mock_graph_service
    # Setup graph ainvoke mock
    mock_graph.ainvoke.return_value = {"output": "result"}

    response = await client.post("/jobs", params={"input_request": "Test Job"}, headers=mock_user_headers)

    expect(response.status_code).to(equal(202))
    data = response.json()
    expect(data).to(have_keys("job_id", "status", "message"))
    expect(data["status"]).to(equal("queued"))


@pytest.mark.asyncio
async def test_create_job_unauthorized(client: AsyncClient):
    # No headers or invalid headers
    invalid_headers = {"X-Tenant-ID": "default", "X-Role": "GUEST", "X-User-ID": "guest"}
    response = await client.post("/jobs", params={"input_request": "Fail"}, headers=invalid_headers)
    expect(response.status_code).to(equal(403))


@pytest.mark.asyncio
async def test_get_agents_summary(client: AsyncClient, mock_agent_registry, mock_user_headers):
    # This endpoint moved from /agents to /agents/summary
    # Wait, in main.py we removed app.get("/agents") and added router /agents
    # The router agents.py has router.get("/summary").
    # So the path is /agents/summary
    response = await client.get("/agents/summary", headers=mock_user_headers)
    expect(response.status_code).to(equal(200))
    data = response.json()
    expect(data).to(be_a(list))
    expect(len(data)).to(equal(2))
    expect(data[0]["id"]).to(equal(MOCK_AGENT_LIST[0].name))


@pytest.mark.asyncio
async def test_list_conversations(client: AsyncClient, db_pool_mock, mock_db_cursor, mock_user_headers):
    # Mock DB return
    now = datetime.now(timezone.utc)
    mock_db_cursor.fetchall.return_value = [(1, "thread-1", "Title 1", now, now), (2, "thread-2", "Title 2", now, now)]

    response = await client.get("/history/conversations", headers=mock_user_headers)
    expect(response.status_code).to(equal(200))
    data = response.json()
    expect(len(data)).to(equal(2))
    expect(data[0]["thread_id"]).to(equal("thread-1"))


@pytest.mark.asyncio
async def test_delete_conversation(client: AsyncClient, db_pool_mock, mock_user_headers):
    response = await client.delete("/history/thread-1", headers=mock_user_headers)
    expect(response.status_code).to(equal(200))
    expect(response.json()).to(have_keys("status", "message"))


@pytest.mark.asyncio
async def test_fork_conversation(client: AsyncClient, mock_graph_service, mock_user_headers):
    _, mock_graph = mock_graph_service

    # Mock aget_state for target checkpoint
    mock_state = MagicMock()
    mock_state.created_at = datetime.now(timezone.utc).isoformat()
    mock_state.values = {"input_request": "Old Input"}
    mock_graph.aget_state.return_value = mock_state

    # Mock aupdate_state
    mock_graph.aupdate_state = AsyncMock()

    response = await client.post(
        "/history/fork?thread_id=t1&checkpoint_id=cp1&new_input=New", headers=mock_user_headers
    )

    expect(response.status_code).to(equal(200))
    expect(response.json()).to(have_keys("status", "message"))
    expect(mock_graph.aupdate_state.called).to(equal(True))


@pytest.mark.asyncio
async def test_fork_conversation_not_found(client: AsyncClient, mock_graph_service, mock_user_headers):
    _, mock_graph = mock_graph_service
    mock_graph.aget_state.return_value = None

    response = await client.post("/history/fork?thread_id=t1&checkpoint_id=cp1", headers=mock_user_headers)
    expect(response.status_code).to(equal(200))
    expect(response.json()).to(equal({"error": "Checkpoint not found"}))


@pytest.mark.asyncio
async def test_get_step_history(
    client: AsyncClient, db_pool_mock, mock_db_cursor, mock_graph_service, mock_agent_registry, mock_user_headers
):
    # 1. Mock DB Logs
    now = datetime.now(timezone.utc)
    mock_db_cursor.fetchall.return_value = [(1, "t1", "tool_execution", "tool_output", "Result", now, "cp2")]

    # 2. Mock Graph Checkpoints
    _, mock_graph = mock_graph_service

    # Mocking aget_state_history generator
    mock_state1 = MagicMock()
    mock_state1.config = {"configurable": {"checkpoint_id": "cp1"}}
    mock_state1.parent_config = None
    mock_state1.metadata = {"langgraph_node": "preprocess"}
    mock_state1.created_at = now.isoformat()

    mock_state2 = MagicMock()
    mock_state2.config = {"configurable": {"checkpoint_id": "cp2"}}
    mock_state2.parent_config = {"configurable": {"checkpoint_id": "cp1"}}
    mock_state2.metadata = {"langgraph_node": "tool_execution"}
    mock_state2.created_at = now.isoformat()

    async def history_gen(*args, **kwargs):
        yield mock_state1
        yield mock_state2

    mock_graph.aget_state_history = history_gen

    response = await client.get("/history/t1/steps", headers=mock_user_headers)
    expect(response.status_code).to(equal(200))
    data = response.json()

    expect(len(data)).to(equal(3))

    types = [item["log_type"] for item in data]

    expect(types).to(contain("node_start"))
    expect(types).to(contain("tool_output"))
