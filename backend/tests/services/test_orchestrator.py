from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from expects import contain, equal, expect

from models.state import AgentResult
from services.orchestrator import OrchestratorService


@pytest.fixture
def mock_agent_registry():
    with patch("services.orchestrator.AgentRegistry") as MockRegistry:
        mock_instance = MockRegistry.return_value

        # Mock available agents
        agent1 = MagicMock()
        agent1.name = "agent1_name"
        agent1.display_name = "AGENT1"
        agent1.description = "Agent 1 Desc"
        agent1.agent.role = "Role 1"
        agent1.agent.goal = "Goal 1"

        mock_instance.get_all.return_value = [agent1]

        yield mock_instance


@pytest.fixture
def mock_llm_call():
    with patch("services.orchestrator.llm") as MockLLM:
        MockLLM.acall = AsyncMock()
        yield MockLLM


@pytest.mark.asyncio
async def test_decide_next_step_qa(mock_agent_registry, mock_llm_call):
    service = OrchestratorService()

    mock_llm_call.acall.return_value = "QA"

    steps = await service.decide_next_step("Done?", [])

    expect(steps).to(equal(["qa"]))


@pytest.mark.asyncio
async def test_decide_next_step_tools(mock_agent_registry, mock_llm_call):
    service = OrchestratorService()

    mock_llm_call.acall.return_value = "TOOLS"

    steps = await service.decide_next_step("Run tool", [])

    expect(steps).to(equal(["tool_planning"]))


@pytest.mark.asyncio
async def test_decide_next_step_agent(mock_agent_registry, mock_llm_call):
    service = OrchestratorService()

    mock_llm_call.acall.return_value = "AGENT1"

    steps = await service.decide_next_step("Use agent", [])

    expect(steps).to(equal(["agent1_name"]))


@pytest.mark.asyncio
async def test_decide_next_step_multiple(mock_agent_registry, mock_llm_call):
    service = OrchestratorService()

    mock_llm_call.acall.return_value = "AGENT1, TOOLS"

    steps = await service.decide_next_step("Multi", [])

    # Order depends on iteration implementation usually, but here list comprehension preserves input order
    expect(steps).to(contain("agent1_name"))
    expect(steps).to(contain("tool_planning"))


@pytest.mark.asyncio
async def test_decide_next_step_unknown_fallback(mock_agent_registry, mock_llm_call):
    service = OrchestratorService()

    mock_llm_call.acall.return_value = "UNKNOWN"

    steps = await service.decide_next_step("Multi", [])

    # Fallback to QA
    expect(steps).to(equal(["qa"]))


@pytest.mark.asyncio
async def test_decide_next_step_with_history(mock_agent_registry, mock_llm_call):
    service = OrchestratorService()

    mock_llm_call.acall.return_value = "QA"

    # Create valid AgentResult
    history = [AgentResult(task_id="t1", summary="Sum", raw_output="Raw", metadata={})]

    steps = await service.decide_next_step("Context", history, context="Ctx")

    expect(steps).to(equal(["qa"]))
    # Verify prompt construction if needed, but integration test covers that better.
    # Unit test assumes LLM behaves based on implementation which is mocked here.
