from unittest.mock import AsyncMock, patch

import pytest
from expects import contain, equal, expect
from httpx import AsyncClient

from brain.registry import AgentConfig, NodeConfig, TaskConfig

# Mocks
MOCK_NODE_CONFIG = NodeConfig(
    name="test_agent",
    display_name="Test Agent",
    description="Desc",
    output_state_key="test_key",
    agent=AgentConfig(role="Role", goal="Goal", backstory="Backstory"),
    task=TaskConfig(description="Task", expected_output="Output"),
)


@pytest.fixture
def mock_agent_registry_agents():
    """Mock AgentRegistry methods."""
    with patch("api.v1.endpoints.agents.AgentRegistry") as MockRegistry:
        mock_instance = MockRegistry.return_value
        mock_instance.get_all.return_value = [MOCK_NODE_CONFIG]
        mock_instance.get_config.return_value = MOCK_NODE_CONFIG
        mock_instance.save_agent = AsyncMock()
        mock_instance.delete_agent = AsyncMock()
        yield mock_instance


@pytest.fixture
def mock_graph_service_agents():
    with patch("services.graph_service.GraphService") as MockService:
        mock_instance = MockService.get_instance.return_value
        mock_instance.reload_graph = AsyncMock()
        yield mock_instance


@pytest.fixture
def mock_llm_call():
    with patch("api.v1.endpoints.agents.llm") as MockLLM:
        # Mocking llm.call to return a valid YAML string
        yaml_resp = """
name: generated_agent
display_name: Generated Agent
description: Generated Desc
output_state_key: gen_key
agent:
  role: Gen Role
  goal: Gen Goal
  backstory: Gen Backstory
  files_access: true
task:
  description: Gen Task with {request}
  expected_output: Gen Output
"""
        MockLLM.call.return_value = yaml_resp
        yield MockLLM


@pytest.mark.asyncio
async def test_list_agents(client: AsyncClient, mock_agent_registry_agents, mock_user_headers):
    response = await client.get("/agents/", headers=mock_user_headers)
    expect(response.status_code).to(equal(200))
    data = response.json()
    expect(len(data)).to(equal(1))
    expect(data[0]["name"]).to(equal("test_agent"))


@pytest.mark.asyncio
async def test_get_agent_found(client: AsyncClient, mock_agent_registry_agents, mock_user_headers):
    response = await client.get("/agents/test_agent", headers=mock_user_headers)
    expect(response.status_code).to(equal(200))
    data = response.json()
    expect(data["name"]).to(equal("test_agent"))


@pytest.mark.asyncio
async def test_get_agent_not_found(client: AsyncClient, mock_agent_registry_agents, mock_user_headers):
    mock_agent_registry_agents.get_config.return_value = None
    response = await client.get("/agents/unknown_agent", headers=mock_user_headers)
    expect(response.status_code).to(equal(404))


@pytest.mark.asyncio
async def test_create_or_update_agent_success(
    client: AsyncClient, mock_agent_registry_agents, mock_graph_service_agents, mock_admin_headers
):
    payload = MOCK_NODE_CONFIG.model_dump()
    response = await client.post("/agents/", json=payload, headers=mock_admin_headers)
    expect(response.status_code).to(equal(200))
    expect(mock_agent_registry_agents.save_agent.called).to(equal(True))
    # Check graph reload called
    mock_graph_service_agents.reload_graph.assert_called()


@pytest.mark.asyncio
async def test_create_agent_forbidden_mcp_config(
    client: AsyncClient, mock_agent_registry_agents, mock_db_cursor, mock_admin_headers
):
    # Mock DB config to have RESTRICTED allowed_mcp_servers
    # The code queries 'infrastructure_config'.
    mock_db_cursor.fetchone.return_value = ({"allowed_mcp_servers": ["server1"]},)

    config = MOCK_NODE_CONFIG.model_copy()
    config.agent.mcp_servers = ["server1", "forbidden_server"]
    payload = config.model_dump()

    response = await client.post("/agents/", json=payload, headers=mock_admin_headers)
    expect(response.status_code).to(equal(403))
    expect(response.json()["detail"]).to(equal("MCP servers not allowed for this tenant: ['forbidden_server']"))


@pytest.mark.asyncio
async def test_delete_agent_success(
    client: AsyncClient, mock_agent_registry_agents, mock_graph_service_agents, mock_admin_headers
):
    response = await client.delete("/agents/test_agent", headers=mock_admin_headers)
    expect(response.status_code).to(equal(200))
    expect(mock_agent_registry_agents.delete_agent.called).to(equal(True))


@pytest.mark.asyncio
async def test_delete_agent_not_found(client: AsyncClient, mock_agent_registry_agents, mock_admin_headers):
    mock_agent_registry_agents.get_config.return_value = None
    response = await client.delete("/agents/unknown", headers=mock_admin_headers)
    expect(response.status_code).to(equal(404))


@pytest.mark.asyncio
async def test_generate_agent_success(client: AsyncClient, mock_llm_call, mock_db_cursor, mock_admin_headers):
    # Mock Valid Infrastructure
    mock_db_cursor.fetchone.return_value = ({"local_workspace_path": "/tmp", "s3_access": True},)

    payload = {"prompt": "Create an agent", "files_access": True, "s3_access": False}
    response = await client.post("/agents/generate", json=payload, headers=mock_admin_headers)
    expect(response.status_code).to(equal(200))
    data = response.json()
    expect(data["name"]).to(equal("generated_agent"))
    # Check if implicit instruction was added (Line 210 coverage)
    expect(data["task"]["description"]).to(contain("AsyncFileWriteTool"))


@pytest.mark.asyncio
async def test_generate_agent_forbidden_files(client: AsyncClient, mock_db_cursor, mock_admin_headers):
    # Mock missing local_workspace_path
    mock_db_cursor.fetchone.return_value = ({"s3_access": True},)  # No local path

    payload = {
        "prompt": "Create an agent",
        "files_access": True,  # Should fail
        "s3_access": False,
    }
    response = await client.post("/agents/generate", json=payload, headers=mock_admin_headers)
    expect(response.status_code).to(equal(403))


@pytest.mark.asyncio
async def test_generate_agent_forbidden_s3(client: AsyncClient, mock_db_cursor, mock_admin_headers):
    # Mock missing s3_access in infra
    mock_db_cursor.fetchone.return_value = ({"local_workspace_path": "/tmp"},)  # No s3_access

    payload = {
        "prompt": "Create an agent",
        "s3_access": True,  # Should fail
    }
    response = await client.post("/agents/generate", json=payload, headers=mock_admin_headers)
    expect(response.status_code).to(equal(403))
    expect(response.json()["detail"]).to(contain("S3 Access is not configured"))


@pytest.mark.asyncio
async def test_generate_agent_forbidden_mcp(client: AsyncClient, mock_db_cursor, mock_admin_headers):
    # Mock restricted MCP servers
    mock_db_cursor.fetchone.return_value = ({"local_workspace_path": "/tmp", "allowed_mcp_servers": ["s1"]},)

    payload = {
        "prompt": "Create an agent",
        "mcp_servers": ["s1", "FORBIDDEN"],  # Should fail
    }
    response = await client.post("/agents/generate", json=payload, headers=mock_admin_headers)
    expect(response.status_code).to(equal(403))
    expect(response.json()["detail"]).to(contain("MCP servers not allowed"))


@pytest.mark.asyncio
async def test_generate_agent_infra_fetch_error(client: AsyncClient, mock_llm_call, mock_db_cursor, mock_admin_headers):
    # Simulate DB error during infra fetch (Lines 136-137)
    mock_db_cursor.execute.side_effect = Exception("DB Error")

    # Should default to empty infra_data and proceed (unless permissions allow checking nulls)
    # The code prints warning and continues.
    # But then checks permissions. If we request s3_access=True with empty infra, it should fail.
    # Start with minimal request that doesn't rely on infra
    payload = {"prompt": "Create an agent", "files_access": False, "s3_access": False}

    response = await client.post("/agents/generate", json=payload, headers=mock_admin_headers)
    # It should succeed to generate, just with empty infra context
    expect(response.status_code).to(equal(200))


@pytest.mark.asyncio
async def test_list_mcp_servers(client: AsyncClient, mock_db_cursor, mock_user_headers):
    mock_db_cursor.fetchall.return_value = [("server1",), ("server2",)]
    response = await client.get("/agents/mcp/servers", headers=mock_user_headers)
    expect(response.status_code).to(equal(200))
    expect(response.json()).to(equal(["server1", "server2"]))


@pytest.mark.asyncio
async def test_create_or_update_agent_db_error(
    client: AsyncClient, mock_agent_registry_agents, mock_graph_service_agents, mock_db_cursor, mock_admin_headers
):
    # Simulate DB error during MCP validation
    mock_db_cursor.execute.side_effect = Exception("DB Error")
    payload = MOCK_NODE_CONFIG.model_dump()
    config = MOCK_NODE_CONFIG.model_copy()
    config.agent.mcp_servers = ["s1"]  # Trigger validation logic
    payload = config.model_dump()

    # The code catches generic Exception and prints warning, then proceeds.
    # So we expect 200, but we want to ensure it didn't crash.
    response = await client.post("/agents/", json=payload, headers=mock_admin_headers)
    expect(response.status_code).to(equal(200))


@pytest.mark.asyncio
async def test_create_or_update_agent_save_error(client: AsyncClient, mock_agent_registry_agents, mock_admin_headers):
    mock_agent_registry_agents.save_agent.side_effect = Exception("Save Failed")
    payload = MOCK_NODE_CONFIG.model_dump()
    response = await client.post("/agents/", json=payload, headers=mock_admin_headers)
    expect(response.status_code).to(equal(500))
    expect(response.json()["detail"]).to(contain("Failed to save agent"))


@pytest.mark.asyncio
async def test_delete_agent_error(client: AsyncClient, mock_agent_registry_agents, mock_admin_headers):
    mock_agent_registry_agents.delete_agent.side_effect = Exception("Delete Failed")
    response = await client.delete("/agents/test_agent", headers=mock_admin_headers)
    expect(response.status_code).to(equal(500))
    expect(response.json()["detail"]).to(contain("Failed to delete agent"))


@pytest.mark.asyncio
async def test_generate_agent_llm_error(client: AsyncClient, mock_llm_call, mock_db_cursor, mock_admin_headers):
    mock_llm_call.call.side_effect = Exception("LLM connection error")
    mock_db_cursor.fetchone.return_value = ({"local_workspace_path": "/tmp", "s3_access": True},)
    payload = {"prompt": "Create an agent", "files_access": True}

    response = await client.post("/agents/generate", json=payload, headers=mock_admin_headers)
    expect(response.status_code).to(equal(500))
    expect(response.json()["detail"]).to(contain("Failed to generate agent"))


@pytest.mark.asyncio
async def test_list_mcp_servers_error(client: AsyncClient, mock_db_cursor, mock_user_headers):
    mock_db_cursor.execute.side_effect = Exception("DB Error")
    response = await client.get("/agents/mcp/servers", headers=mock_user_headers)
    # Code catches exception and returns empty list
    expect(response.status_code).to(equal(200))
    expect(response.json()).to(equal([]))
