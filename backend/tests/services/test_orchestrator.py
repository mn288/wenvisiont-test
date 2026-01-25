from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from expects import contain, equal, expect

from services.orchestrator import OrchestratorDecision, OrchestratorService


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
        agent1.agent.importance_score = 0.5
        agent1.agent.success_rate = 0.9
        agent1.agent.task_domains = []

        mock_instance.get_all.return_value = [agent1]
        mock_instance.get_workflows.return_value = []

        yield mock_instance


@pytest.fixture
def mock_llm_call():
    """Mock the structured LLM call used by OrchestratorService."""
    with patch("services.orchestrator.llm") as MockLLM:
        # The service uses llm.client.with_structured_output().ainvoke()
        mock_structured = MagicMock()
        MockLLM.client.with_structured_output.return_value = mock_structured
        mock_structured.ainvoke = AsyncMock()
        yield mock_structured


@pytest.mark.asyncio
async def test_decide_next_step_qa(mock_agent_registry, mock_llm_call):
    service = OrchestratorService()

    # Mock structured output return
    mock_llm_call.ainvoke.return_value = OrchestratorDecision(
        thought_process="Task is complete", reasoning="User asked if done", selected_agents=["QA"], plan=[]
    )

    steps, plan = await service.decide_next_step(
        request="Done?", global_state={}, long_term_summary="", conversation_buffer=[], current_plan=[]
    )

    expect(steps).to(equal(["qa"]))
    expect(plan).to(equal([]))


@pytest.mark.asyncio
async def test_decide_next_step_agent(mock_agent_registry, mock_llm_call):
    service = OrchestratorService()

    mock_llm_call.ainvoke.return_value = OrchestratorDecision(
        thought_process="Need to use agent", reasoning="User requested agent", selected_agents=["AGENT1"], plan=[]
    )

    steps, plan = await service.decide_next_step(
        request="Use agent", global_state={}, long_term_summary="", conversation_buffer=[], current_plan=[]
    )

    expect(steps).to(equal(["agent1_name"]))


@pytest.mark.asyncio
async def test_decide_next_step_multiple(mock_agent_registry, mock_llm_call):
    service = OrchestratorService()

    mock_llm_call.ainvoke.return_value = OrchestratorDecision(
        thought_process="Need multiple agents", reasoning="Complex task", selected_agents=["AGENT1", "QA"], plan=[]
    )

    steps, plan = await service.decide_next_step(
        request="Multi", global_state={}, long_term_summary="", conversation_buffer=[], current_plan=[]
    )

    # Both should be in the result
    expect(steps).to(contain("agent1_name"))
    expect(steps).to(contain("qa"))


@pytest.mark.asyncio
async def test_decide_next_step_unknown_fallback(mock_agent_registry, mock_llm_call):
    service = OrchestratorService()

    mock_llm_call.ainvoke.return_value = OrchestratorDecision(
        thought_process="Unknown agent", reasoning="Fallback needed", selected_agents=["UNKNOWN"], plan=[]
    )

    steps, plan = await service.decide_next_step(
        request="Multi", global_state={}, long_term_summary="", conversation_buffer=[], current_plan=[]
    )

    # Fallback to QA when no valid agents found
    expect(steps).to(equal(["qa"]))


@pytest.mark.asyncio
async def test_decide_next_step_with_context(mock_agent_registry, mock_llm_call):
    service = OrchestratorService()

    mock_llm_call.ainvoke.return_value = OrchestratorDecision(
        thought_process="Context analyzed", reasoning="Proceeding with QA", selected_agents=["QA"], plan=[]
    )

    # Mock hybrid context
    global_state = {"result": 42}
    summary = "Previously did X."
    buffer = ["User: Do Y"]

    steps, plan = await service.decide_next_step(
        request="Context",
        global_state=global_state,
        long_term_summary=summary,
        conversation_buffer=buffer,
        current_plan=["step1", "step2"],
    )

    expect(steps).to(equal(["qa"]))


@pytest.mark.asyncio
async def test_decide_next_step_returns_plan(mock_agent_registry, mock_llm_call):
    service = OrchestratorService()

    mock_llm_call.ainvoke.return_value = OrchestratorDecision(
        thought_process="Planning ahead",
        reasoning="Multi-step task",
        selected_agents=["AGENT1"],
        plan=["step2", "step3"],
    )

    steps, plan = await service.decide_next_step(
        request="Plan task", global_state={}, long_term_summary="", conversation_buffer=[], current_plan=[]
    )

    expect(steps).to(equal(["agent1_name"]))
    expect(plan).to(equal(["step2", "step3"]))
