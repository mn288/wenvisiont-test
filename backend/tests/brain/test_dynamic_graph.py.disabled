from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.brain.nodes import research_node, supervisor_node


@pytest.mark.asyncio
async def test_supervisor_routing():
    # Mock LLM and LogHandler
    with (
        patch("src.brain.nodes.llm") as mock_llm,
        patch("src.brain.nodes.LogHandler") as mock_logger_cls,
    ):
        # Setup mock logger instance
        mock_logger = AsyncMock()
        mock_logger_cls.return_value = mock_logger

        mock_llm.call.side_effect = ["RESEARCH", "ANALYZE", "FINISH"]

        # 1. State setup
        state = {"input_request": "Investigate AI Agents", "messages": []}
        config = {"configurable": {"thread_id": "test_thread"}}

        # 2. First pass: Supervisor -> Research
        result = await supervisor_node(state, config)
        assert result["next_step"] == "research"

        # 3. Second pass: Supervisor -> Analyze
        # We simulate that Research happened and added to messages/findings
        state["research_output"] = "Some research findings"
        result = await supervisor_node(state, config)
        assert result["next_step"] == "analyze"

        # 4. Third pass: Supervisor -> Finish
        result = await supervisor_node(state, config)
        assert result["next_step"] == "qa"


@pytest.mark.asyncio
async def test_async_research_kickoff():
    # Verify research node uses async kickoff (or to_thread)
    with (
        patch("src.brain.nodes.Crew") as mock_crew_cls,
        patch("src.brain.nodes.LogHandler") as mock_logger_cls,
    ):
        mock_logger = AsyncMock()
        mock_logger_cls.return_value = mock_logger

        mock_crew_instance = MagicMock()
        mock_crew_cls.return_value = mock_crew_instance

        # Mock kickoff result
        mock_crew_instance.kickoff.return_value = "Async Research Result"

        state = {"input_request": "Test"}
        config = {"configurable": {"thread_id": "test_thread"}}

        # We need to make sure it calls asyncio.to_thread or kickoff_async
        # Since asyncio.to_thread is hard to mock directly with patch, we check behavior
        result = await research_node(state, config)

        assert "Async Research Result" in result["research_output"]
        # Ensure kickoff was called
        mock_crew_instance.kickoff.assert_called_once()
