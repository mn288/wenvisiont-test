from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.brain.nodes import execute_agent_node
from src.brain.registry import AgentConfig, NodeConfig, TaskConfig


@pytest.mark.asyncio
async def test_execute_agent_node_crew_output():
    """Verify execute_agent_node correctly appends to crew_output list."""
    # Mock Registry and Config
    mock_registry = MagicMock()
    mock_config = NodeConfig(
        name="writer",
        display_name="WRITER",
        description="Writes content",
        output_state_key="crew_output",
        agent=AgentConfig(role="Writer", goal="Write", backstory="Writes"),
        task=TaskConfig(description="Write task", expected_output="Content"),
    )
    mock_registry.get_config.return_value = mock_config

    # Mock Crew execution
    mock_crew = MagicMock()
    mock_crew.akickoff = AsyncMock(return_value="Generated Content")

    with (
        patch("src.brain.nodes.AgentRegistry", return_value=mock_registry),
        patch("src.brain.nodes.Crew", return_value=mock_crew),
        patch("src.brain.nodes.summarize_content", new_callable=AsyncMock) as mock_summ,
        patch("src.brain.nodes.llm", new=AsyncMock()),
        patch("src.brain.nodes.LogHandler") as mock_logger,
    ):  # Mock global llm if needed
        # Configure logger mock
        mock_logger.return_value.log_step = AsyncMock()

        mock_summ.return_value = "Summary of content"

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
        assert "crew_output" in result
        assert isinstance(result["crew_output"], list)
        assert len(result["crew_output"]) == 1
        output_item = result["crew_output"][0]
        # Depending on implementation, it might be a dict (from model_dump) or object
        assert output_item["summary"] == "Summary of content"
        assert output_item["raw_output"] == "Generated Content"


@pytest.mark.asyncio
async def test_execute_agent_node_research_output():
    """Verify execute_agent_node correctly appends to research_output string."""
    # Mock Registry and Config
    mock_registry = MagicMock()
    mock_config = NodeConfig(
        name="researcher",
        display_name="RESEARCHER",
        description="Researches",
        output_state_key="research_output",
        agent=AgentConfig(role="Researcher", goal="Research", backstory="Researches"),
        task=TaskConfig(description="Research task", expected_output="Findings"),
    )
    mock_registry.get_config.return_value = mock_config

    # Mock Crew execution
    mock_crew = MagicMock()
    mock_crew.akickoff = AsyncMock(return_value="New Findings")

    with (
        patch("src.brain.nodes.AgentRegistry", return_value=mock_registry),
        patch("src.brain.nodes.Crew", return_value=mock_crew),
        patch("src.brain.nodes.summarize_content", new_callable=AsyncMock) as mock_summ,
        patch("src.brain.nodes.LogHandler") as mock_logger,
    ):
        mock_logger.return_value.log_step = AsyncMock()

        mock_summ.return_value = "Summary of findings"

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
        assert "research_output" in result
        assert isinstance(result["research_output"], str)
        assert "Existing research" in result["research_output"]
        assert "Summary of findings" in result["research_output"]
        # Ensure it didn't overwrite with a list
        assert not isinstance(result["research_output"], list)


@pytest.mark.asyncio
async def test_execute_agent_node_custom_key_fallback():
    """Verify execute_agent_node handles unknown keys safely (string append fallback)."""
    # Mock Registry and Config
    mock_registry = MagicMock()
    mock_config = NodeConfig(
        name="strategist",
        display_name="STRATEGIST",
        description="Plans",
        output_state_key="strategist_output",  # Custom key
        agent=AgentConfig(role="Strategist", goal="Plan", backstory="Plans"),
        task=TaskConfig(description="Plan task", expected_output="Plan"),
    )
    mock_registry.get_config.return_value = mock_config

    # Mock Crew execution
    mock_crew = MagicMock()
    mock_crew.akickoff = AsyncMock(return_value="Strategic Plan")

    with (
        patch("src.brain.nodes.AgentRegistry", return_value=mock_registry),
        patch("src.brain.nodes.Crew", return_value=mock_crew),
        patch("src.brain.nodes.summarize_content", new_callable=AsyncMock) as mock_summ,
        patch("src.brain.nodes.LogHandler") as mock_logger,
    ):
        mock_logger.return_value.log_step = AsyncMock()
        mock_summ.return_value = "Summary of plan"

        # Initial State - key exists as string
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
        assert "strategist_output" in result
        assert isinstance(result["strategist_output"], str)
        assert "Old plan" in result["strategist_output"]
        assert "Summary of plan" in result["strategist_output"]
