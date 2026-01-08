from unittest.mock import MagicMock, patch

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

        mock_instance.get_all.return_value = [node1, node2]
        # By default, validate returns empty list (no invalid types)
        mock_instance.validate_node_names.return_value = []
        yield mock_instance


@pytest.fixture
def mock_llm_call():
    with patch("services.architect_service.llm") as MockLLM:
        yield MockLLM


@pytest.fixture
def mock_mask_pii():
    with patch("services.architect_service.mask_pii") as MockMask:
        MockMask.side_effect = lambda x: x  # Identity function
        yield MockMask


@pytest.mark.asyncio
async def test_generate_graph_config_success(mock_agent_registry, mock_llm_call, mock_mask_pii):
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
    mock_llm_call.call.return_value = valid_json

    config = await service.generate_graph_config("Create a graph")

    expect(config).to(be_a(GraphConfig))
    expect(config.name).to(equal("TestGraph"))
    expect(len(config.nodes)).to(equal(1))
    expect(mock_agent_registry.get_all.called).to(equal(True))
    expect(mock_llm_call.call.called).to(equal(True))


@pytest.mark.asyncio
async def test_generate_graph_config_invalid_json(mock_agent_registry, mock_llm_call, mock_mask_pii):
    service = ArchitectService()

    mock_llm_call.call.return_value = "NOT JSON"

    with pytest.raises(ValueError) as exc:
        await service.generate_graph_config("Prompt")

    expect(str(exc.value)).to(contain("Failed to parse Architect response"))


@pytest.mark.asyncio
async def test_generate_graph_config_invalid_node_type(mock_agent_registry, mock_llm_call, mock_mask_pii):
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
    mock_llm_call.call.return_value = valid_json

    # Mock validation failure
    mock_agent_registry.validate_node_names.return_value = ["INVALID_AGENT"]

    with pytest.raises(ValueError) as exc:
        await service.generate_graph_config("Prompt")

    expect(str(exc.value)).to(contain("Architect generated invalid node types"))
