from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from expects import be_none, contain, equal, expect, have_key, have_len

from brain.registry import AgentConfig, AgentRegistry, NodeConfig, TaskConfig
from models.infrastructure import InfrastructureConfig

# Test Data
SAMPLE_AGENT_CONFIG = NodeConfig(
    name="analyst_agent",
    display_name="Analyst",
    description="Analyzes things",
    output_state_key="analyst_output",
    agent=AgentConfig(
        role="Analyst",
        goal="Analyze",
        backstory="Backstory",
        files_access=True,
        s3_access=True,
        mcp_servers=["server1"],
    ),
    task=TaskConfig(description="Analyze {topic}", expected_output="Analysis"),
)


@pytest.fixture
def mock_tools_modules():
    with (
        patch("tools.adapter.MCPAdapter") as MockAdapter,
    ):
        # Configure Adapter
        mock_adapter_instance = MockAdapter.return_value
        # get_tools is async
        mock_adapter_instance.get_tools = AsyncMock(return_value=[MagicMock(name="mcp_tool")])
        yield


@pytest.fixture
def mock_crew_classes():
    # Patch Agent and Task in the registry module to bypass Pydantic validation of the real classes
    with (
        patch("brain.registry.Agent") as MockAgent,
        patch("brain.registry.Task") as MockTask,
        patch("brain.registry.llm"),
    ):  # Patch llm to avoid validation issues if passed
        # Make Task return a simple object or mock
        MockTask.return_value = MagicMock(description="Task", expected_output="Output")
        # Make Agent return a mock with tools
        mock_agent_instance = MagicMock()
        mock_agent_instance.tools = []
        MockAgent.return_value = mock_agent_instance

        yield MockAgent, MockTask


@pytest_asyncio.fixture
async def registry(db_pool_mock, mock_db_cursor):
    # Reset singleton
    AgentRegistry._instance = None
    registry = AgentRegistry()
    registry._agents = {}
    return registry


@pytest.mark.asyncio
async def test_save_agent(registry, mock_db_cursor):
    await registry.save_agent(SAMPLE_AGENT_CONFIG)
    expect(registry._agents).to(have_key("analyst_agent"))
    expect(mock_db_cursor.execute.called).to(equal(True))


@pytest.mark.asyncio
async def test_load_agents(registry, mock_db_cursor):
    # Mock DB rows
    # row: name, config_dict
    config_dict = SAMPLE_AGENT_CONFIG.model_dump()
    mock_db_cursor.fetchall.return_value = [("analyst_agent", config_dict)]

    await registry.load_agents()

    expect(registry._agents).to(have_key("analyst_agent"))
    expect(registry._agents["analyst_agent"].name).to(equal("analyst_agent"))


@pytest.mark.asyncio
async def test_delete_agent(registry, mock_db_cursor):
    registry._agents["analyst_agent"] = SAMPLE_AGENT_CONFIG
    await registry.delete_agent("analyst_agent")

    expect(registry._agents).not_to(have_key("analyst_agent"))
    expect(mock_db_cursor.execute.called).to(equal(True))


@pytest.mark.asyncio
async def test_create_agent_with_tools(registry, mock_tools_modules, mock_crew_classes, mock_async_session):
    MockAgent, _ = mock_crew_classes
    registry._agents["analyst_agent"] = SAMPLE_AGENT_CONFIG

    # Mock MCP Fetch
    # mcp_service.get_servers_by_names uses select().in_()... exec().all()
    mock_server = MagicMock()
    mock_server.name = "server1"
    mock_server.type = "stdio"
    mock_server.command = "cmd"
    mock_server.args = []
    mock_server.env = {}

    # We need to ensure that when 'server1' is requested, we return this
    mock_async_session.exec.return_value.all.return_value = [mock_server]

    infra_config = InfrastructureConfig(
        local_workspace_path="/tmp/workspace",
        s3_config={
            "bucket_name": "test-bucket",
            "region_name": "us-east-1",
            "aws_access_key_id": "k",
            "aws_secret_access_key": "s",
        },
    )

    agent = await registry.create_agent("analyst_agent", infra=infra_config)

    expect(agent).not_to(be_none)
    # Since we mocked Agent, we check the 'tools' passed to its constructor
    # MockAgent.call_args[1]["tools"]
    call_kwargs = MockAgent.call_args.kwargs
    tools_arg = call_kwargs["tools"]
    # Expect 1 tool because adapter.get_tools returns 1 mock tool
    expect(tools_arg).to(have_len(1))


@pytest.mark.asyncio
async def test_create_task(registry, mock_crew_classes):
    _, MockTask = mock_crew_classes
    registry._agents["analyst_agent"] = SAMPLE_AGENT_CONFIG

    mock_agent = MagicMock()

    task = registry.create_task("analyst_agent", mock_agent, inputs={"topic": "Stocks"})

    expect(task).not_to(be_none)
    # Check MockTask call args
    call_kwargs = MockTask.call_args.kwargs
    description = call_kwargs["description"]

    # We check that description contains necessary parts rather than exact match
    expect(description).to(
        # We check for the presence of instructions, rather than exact strict equality which breaks easily on whitespace changes
        contain("Analyze Stocks")
    )
