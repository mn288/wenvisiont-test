from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langgraph.types import Send

from brain.nodes import execute_agent_node, supervisor_node


@pytest.mark.asyncio
async def test_supervisor_routing():
    # Mock LLM and LogHandler
    with (
        patch("brain.nodes.supervisor.orchestrator_service") as mock_orchestrator,
        patch("brain.nodes.supervisor.LogHandler") as mock_logger_cls,
    ):
        # Setup mock logger instance
        mock_logger = AsyncMock()
        mock_logger_cls.return_value = mock_logger

        # Mock return value: (next_agent_names, new_plan)
        mock_orchestrator.decide_next_step = AsyncMock()
        mock_orchestrator.decide_next_step.side_effect = [
            ("research", []),
            ("analyze", []),
            ("qa", []),
        ]

        # 1. State setup
        state = {"input_request": "Investigate AI Agents", "messages": []}
        config = {"configurable": {"thread_id": "test_thread"}}

        # 2. First pass: Supervisor -> Research
        result = await supervisor_node(state, config)
        # Check if it's a Send object or simple string
        dest = result.goto[0] if isinstance(result.goto, list) else result.goto
        if isinstance(dest, Send):
            assert dest.node == "research"
        else:
            assert dest == "research"

        # 3. Second pass: Supervisor -> Analyze
        # We simulate that Research happened and added to messages/findings
        state["research_output"] = "Some research findings"
        result = await supervisor_node(state, config)
        dest = result.goto[0] if isinstance(result.goto, list) else result.goto
        if isinstance(dest, Send):
            assert dest.node == "analyze"
        else:
            assert dest == "analyze"

        # 4. Third pass: Supervisor -> Finish
        result = await supervisor_node(state, config)
        # QA is usually a direct string
        dest = result.goto[0] if isinstance(result.goto, list) else result.goto
        assert dest == "qa"


@pytest.mark.asyncio
async def test_async_research_kickoff():
    # Verify research node uses async kickoff (or to_thread)
    with (
        patch("brain.nodes.execution.crew_service") as mock_crew_service,
        patch("brain.nodes.execution.LogHandler") as mock_logger_cls,
    ):
        mock_logger = AsyncMock()
        mock_logger_cls.return_value = mock_logger

        mock_result = MagicMock()
        mock_result.summary = "Async Research Result"
        mock_result.raw_output = "Async Research Result"
        mock_result.metadata = {}
        mock_result.model_dump.return_value = {"summary": "Async Research Result"}

        mock_crew_service.execute_task = AsyncMock(return_value=mock_result)

        state = {"input_request": "Test"}
        config = {"configurable": {"thread_id": "test_thread"}}

        # We need to make sure it calls asyncio.to_thread or kickoff_async
        # Since asyncio.to_thread is hard to mock directly with patch, we check behavior
        result = await execute_agent_node(state, config, agent_name="researcher")

        assert "Async Research Result" in result["messages"][0].content
        # Ensure kickoff was called
        mock_crew_service.execute_task.assert_awaited_once()
