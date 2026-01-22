from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from brain.nodes import execute_agent_node
from models.state import AgentResult


@pytest.mark.asyncio
async def test_execute_agent_node_crew_output():
    """Verify execute_agent_node correctly appends to crew_output list."""

    # Mock result from CrewService
    mock_result = MagicMock(spec=AgentResult)
    mock_result.summary = "Summary of content"
    mock_result.raw_output = "Generated Content"
    mock_result.metadata = {}
    mock_result.model_dump.return_value = {
        "summary": "Summary of content",
        "raw_output": "Generated Content",
        "metadata": {},
    }

    with (
        patch("brain.nodes.crew_service") as mock_service,
        patch("brain.nodes.infrastructure_service") as mock_infra_service,
        patch("brain.nodes.LogHandler") as mock_logger,
    ):
        mock_service.execute_task = AsyncMock(return_value=mock_result)
        mock_infra_service.get_or_create_infrastructure.return_value = {}
        mock_logger.return_value.log_step = AsyncMock()

        # Initial State
        state = {
            "input_request": "Write a blog",
            "research_output": "Some research",
            "crew_output": [],
            "structured_history": [],
        }
        config = {"configurable": {"thread_id": "test_thread"}}

        # Execute
        result = await execute_agent_node(state, config, "writer")

        # Verify
        assert "results" in result
        assert isinstance(result["results"], list)
        assert len(result["results"]) == 1
        output_item = result["results"][0]

        assert output_item["summary"] == "Summary of content"
        assert output_item["raw_output"] == "Generated Content"


@pytest.mark.asyncio
async def test_execute_agent_node_research_output():
    """Verify execute_agent_node correctly returns results."""
    # Mock result
    mock_result = MagicMock(spec=AgentResult)
    mock_result.summary = "Summary of findings"
    mock_result.raw_output = "New Findings"
    mock_result.metadata = {}
    mock_result.model_dump.return_value = {
        "summary": "Summary of findings",
        "raw_output": "New Findings",
        "metadata": {},
    }

    with (
        patch("brain.nodes.crew_service") as mock_service,
        patch("brain.nodes.infrastructure_service"),
        patch("brain.nodes.LogHandler") as mock_logger,
    ):
        mock_service.execute_task = AsyncMock(return_value=mock_result)
        mock_logger.return_value.log_step = AsyncMock()

        # Initial State
        state = {
            "input_request": "Research AI",
            "research_output": "Existing research",
            "crew_output": [],
            "structured_history": [],
        }
        config = {"configurable": {"thread_id": "test_thread"}}

        # Execute
        result = await execute_agent_node(state, config, "researcher")

        # Verify
        assert "results" in result
        # The new implementation returns a 'results' list, not specific string keys like 'research_output'
        # The test update reflects the change in nodes.py returning generic "results"
        assert result["results"][0]["summary"] == "Summary of findings"


@pytest.mark.asyncio
async def test_execute_agent_node_custom_key_fallback():
    """Verify execute_agent_node handles execution."""
    # Mock result
    mock_result = MagicMock(spec=AgentResult)
    mock_result.summary = "Summary of plan"
    mock_result.raw_output = "Strategic Plan"
    mock_result.metadata = {}
    mock_result.model_dump.return_value = {"summary": "Summary of plan", "raw_output": "Strategic Plan", "metadata": {}}

    with (
        patch("brain.nodes.crew_service") as mock_service,
        patch("brain.nodes.infrastructure_service"),
        patch("brain.nodes.LogHandler") as mock_logger,
    ):
        mock_service.execute_task = AsyncMock(return_value=mock_result)
        mock_logger.return_value.log_step = AsyncMock()

        # Initial State
        state = {
            "input_request": "Plan launch",
            "strategist_output": "Old plan",
            "crew_output": [],
            "structured_history": [],
        }
        config = {"configurable": {"thread_id": "test_thread"}}

        # Execute
        result = await execute_agent_node(state, config, "strategist")

        # Verify
        assert "results" in result
        assert result["results"][0]["summary"] == "Summary of plan"
