from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.agents import AgentConfig, NodeConfig, TaskConfig
from services.orchestrator import OrchestratorDecision, OrchestratorService


@pytest.mark.asyncio
async def test_qa_exclusivity_logic():
    """
    Verify that if the LLM returns 'RESEARCH_AGENT, QA', the code
    includes both since the implementation doesn't strip QA when other agents are present.
    """
    # Setup Mocks
    mock_registry = MagicMock()

    # Mock Agent Registry to return a valid agent
    mock_agent = NodeConfig(
        name="research_agent",
        display_name="Research Agent",
        description="does research",
        agent=AgentConfig(
            role="Researcher", goal="Research", backstory="I research", importance_score=1.0, success_rate=1.0
        ),
        task=TaskConfig(description="Research task", expected_output="Research results"),
    )
    mock_registry.get_all.return_value = [mock_agent]
    mock_registry.get_workflows.return_value = []

    orchestrator = OrchestratorService()
    orchestrator.registry = mock_registry

    # Test Case 1: Mixed Return from LLM - both agents and QA
    with patch("services.orchestrator.llm") as mock_llm:
        mock_structured = MagicMock()
        mock_llm.client.with_structured_output.return_value = mock_structured
        mock_structured.ainvoke = AsyncMock(
            return_value=OrchestratorDecision(
                thought_process="Need research and QA",
                reasoning="Multi-step",
                selected_agents=["RESEARCH_AGENT", "QA"],
                plan=[],
            )
        )

        decisions, plan = await orchestrator.decide_next_step(
            request="Research AI", global_state={}, long_term_summary="", conversation_buffer=[], current_plan=[]
        )

        # Both should be in decisions
        assert "research_agent" in decisions
        assert "qa" in decisions

    # Test Case 2: Only Agents
    with patch("services.orchestrator.llm") as mock_llm:
        mock_structured = MagicMock()
        mock_llm.client.with_structured_output.return_value = mock_structured
        mock_structured.ainvoke = AsyncMock(
            return_value=OrchestratorDecision(
                thought_process="Need research", reasoning="Single agent", selected_agents=["RESEARCH_AGENT"], plan=[]
            )
        )

        decisions, plan = await orchestrator.decide_next_step(
            request="Research AI", global_state={}, long_term_summary="", conversation_buffer=[], current_plan=[]
        )

        assert "research_agent" in decisions
        assert "qa" not in decisions

    # Test Case 3: Only QA (Valid)
    with patch("services.orchestrator.llm") as mock_llm:
        mock_structured = MagicMock()
        mock_llm.client.with_structured_output.return_value = mock_structured
        mock_structured.ainvoke = AsyncMock(
            return_value=OrchestratorDecision(
                thought_process="Task complete", reasoning="Finalize", selected_agents=["QA"], plan=[]
            )
        )

        decisions, plan = await orchestrator.decide_next_step(
            request="Finished", global_state={}, long_term_summary="", conversation_buffer=[], current_plan=[]
        )

        assert "qa" in decisions
        assert len(decisions) == 1
