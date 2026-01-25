from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from expects import be_a, contain, equal, expect

from models.architect import GraphConfig
from services.architect_service import ArchitectService


@pytest.fixture
def mock_agent_registry():
    with patch("services.architect_service.AgentRegistry") as MockRegistry:
        mock_instance = MockRegistry.return_value
        # Mock available nodes
        node1 = MagicMock()
        node1.name = "agent1"
        node1.description = "Agent 1 Description"

        node2 = MagicMock()
        node2.name = "agent2"
        node2.description = "Agent 2 Description"

        # Mock available workflows (Superagents)
        mock_instance.get_workflows.return_value = [node1, node2]

        # get_all returns individual agents (not used for validation anymore in 1st step)
        mock_instance.get_all.return_value = [node1, node2]
        # By default, validate returns empty list (no invalid types)
        mock_instance.validate_node_names.return_value = []
        yield mock_instance


@pytest.fixture
def mock_tool_service():
    with patch("services.architect_service.tool_service") as MockToolService:
        MockToolService.get_server_tool_map = AsyncMock(return_value={})
        yield MockToolService


@pytest.fixture
def mock_masker():
    with patch("services.architect_service.masker") as MockMasker:
        MockMasker.mask.side_effect = lambda x: x  # Identity function
        yield MockMasker


@pytest.mark.asyncio
async def test_generate_graph_config_success(mock_agent_registry, mock_tool_service, mock_masker):
    service = ArchitectService()

    # Mock LLM good response
    valid_json = """
    {
      "name": "TestGraph",
      "description": "A test graph",
      "nodes": [
        { "id": "n1", "type": "agent1", "config": {} }
      ],
      "edges": []
    }
    """

    # Mock the llm attribute on the service instance
    service.llm = MagicMock()
    service.llm.acall = AsyncMock(return_value=valid_json)

    config = await service.create_plan("test-request-id", {"goal": "Create a graph"})

    expect(config).to(be_a(GraphConfig))
    expect(config.name).to(equal("TestGraph"))
    expect(len(config.nodes)).to(equal(1))
    expect(mock_agent_registry.get_workflows.called).to(equal(True))
    expect(service.llm.acall.called).to(equal(True))


@pytest.mark.asyncio
async def test_generate_graph_config_invalid_json(mock_agent_registry, mock_tool_service, mock_masker):
    service = ArchitectService()

    # Mock the llm attribute on the service instance
    service.llm = MagicMock()
    service.llm.acall = AsyncMock(return_value="NOT JSON")

    with pytest.raises(ValueError) as exc:
        await service.create_plan("test-request-id", {"goal": "Prompt"})

    expect(str(exc.value)).to(contain("Failed to parse Architect response"))


@pytest.mark.asyncio
async def test_generate_graph_config_invalid_node_type(mock_agent_registry, mock_tool_service, mock_masker):
    service = ArchitectService()

    valid_json = """
    {
      "name": "TestGraph",
      "description": "A test graph",
      "nodes": [
        { "id": "n1", "type": "INVALID_AGENT", "config": {} }
      ],
      "edges": []
    }
    """

    # Mock the llm attribute on the service instance
    service.llm = MagicMock()
    service.llm.acall = AsyncMock(return_value=valid_json)

    # Mock validation failure
    mock_agent_registry.validate_node_names.return_value = ["INVALID_AGENT"]

    with pytest.raises(ValueError) as exc:
        await service.create_plan("test-request-id", {"goal": "Prompt"})

    expect(str(exc.value)).to(contain("Architect generated invalid node types"))
