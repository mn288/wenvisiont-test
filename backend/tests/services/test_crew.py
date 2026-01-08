from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from expects import contain, equal, expect, have_keys

from models.state import AgentTask
from services.crew import CrewService


@pytest.fixture
def mock_agent_registry():
    with patch("services.crew.AgentRegistry") as MockRegistry:
        mock_instance = MockRegistry.return_value

        # Mock global config getter
        mock_config = MagicMock()
        mock_config.agent.role = "Test Role"
        mock_instance.get_config.return_value = mock_config

        # Mock factory methods
        mock_agent = MagicMock()
        mock_agent.llm.model = "gpt-4-test"
        mock_instance.create_agent = AsyncMock(return_value=mock_agent)

        mock_task = MagicMock()
        mock_instance.create_task.return_value = mock_task

        yield mock_instance


@pytest.fixture
def mock_crew():
    with patch("services.crew.Crew") as MockCrew:
        mock_instance = MockCrew.return_value
        yield MockCrew, mock_instance


@pytest.mark.asyncio
async def test_execute_task_success(mock_agent_registry, mock_crew):
    MockCrewClass, mock_crew_instance = mock_crew

    # Mock result
    mock_result = MagicMock()
    mock_result.__str__.return_value = "Task Result Output"
    mock_result.token_usage = {"total_tokens": 100}
    mock_crew_instance.akickoff = AsyncMock(return_value=mock_result)

    service = CrewService()
    task = AgentTask(id="task1", name="agent1", type="crew", assigned_to="Agent One", input_data="Do work")

    result = await service.execute_task(task, context="Context")

    expect(result.task_id).to(equal("task1"))
    expect(result.raw_output).to(equal("Task Result Output"))
    expect(result.metadata).to(have_keys("agent_role", "model", "usage"))
    expect(result.metadata["usage"]).to(equal({"total_tokens": 100}))

    # Verify calls
    expect(mock_agent_registry.create_agent.called).to(equal(True))
    expect(mock_agent_registry.create_task.called).to(equal(True))
    expect(mock_crew_instance.akickoff.called).to(equal(True))


@pytest.mark.asyncio
async def test_execute_task_agent_not_found(mock_agent_registry, mock_crew):
    service = CrewService()
    mock_agent_registry.get_config.return_value = None

    task = AgentTask(id="task1", name="unknown", type="crew", assigned_to="Unknown", input_data="Do work")

    with pytest.raises(ValueError) as exc:
        await service.execute_task(task)

    expect(str(exc.value)).to(contain("Agent unknown not found"))


@pytest.mark.asyncio
async def test_execute_task_no_usage_metadata(mock_agent_registry, mock_crew):
    MockCrewClass, mock_crew_instance = mock_crew

    # Mock result w/o token usage (or empty)
    mock_result = MagicMock()
    mock_result.__str__.return_value = "Output"
    # Ensure token_usage is a dict directly, simulating Pydantic model vs dict vs missing
    mock_result.token_usage = {}
    mock_crew_instance.akickoff = AsyncMock(return_value=mock_result)

    service = CrewService()
    task = AgentTask(id="task1", name="agent1", type="crew", assigned_to="Agent One", input_data="Do work")

    result = await service.execute_task(task)

    expect(result.metadata["usage"]).to(equal({}))
