from brain.prompts import (
    DYNAMIC_AGENT_BACKSTORY,
    DYNAMIC_AGENT_GOAL,
    DYNAMIC_AGENT_ROLE,
    DYNAMIC_AGENT_TASK,
    ORCHESTRATOR_PROMPT,
    QA_AGGREGATION_PROMPT,
    REFLECTION_PROMPT,
)


def test_orchestrator_prompt_formatting():
    """Verify ORCHESTRATOR_PROMPT accepts all expected keys."""
    formatted = ORCHESTRATOR_PROMPT.format(
        request="Test Request",
        current_time="2023-01-01 12:00:00",
        state_json="{}",
        long_term_summary="Summary",
        history_display="History",
        dynamic_agents_desc="Agents",
        last_agent_name="None",
        last_agent_status_msg="OK",
        current_plan="['step1', 'step2']",
    )
    assert "Test Request" in formatted
    assert "2023-01-01" in formatted
    assert "step1" in formatted


def test_dynamic_agent_prompts_formatting():
    """Verify Dynamic Agent prompts."""
    # Role
    role = DYNAMIC_AGENT_ROLE.format(server_name="TestServer")
    assert "TestServer Specialist" in role

    # Goal - Note: DYNAMIC_AGENT_GOAL is a static string without placeholders
    goal = DYNAMIC_AGENT_GOAL
    assert "function-calling" in goal

    # Backstory
    backstory = DYNAMIC_AGENT_BACKSTORY.format(server_name="TestServer", tool_summary="Tool1, Tool2")
    assert "TestServer" in backstory
    assert "Tool1, Tool2" in backstory

    # Task
    task = DYNAMIC_AGENT_TASK.format(request="Do work")
    assert "Do work" in task


def test_reflection_prompt_formatting():
    """Verify Reflection prompt."""
    formatted = REFLECTION_PROMPT.format(input_request="Request", raw_output="Output")
    assert "Request" in formatted
    assert "Output" in formatted


def test_qa_aggregation_prompt_formatting():
    """Verify QA Aggregation prompt."""
    formatted = QA_AGGREGATION_PROMPT.format(input_request="Request", full_context="Context")
    assert "Request" in formatted
    assert "Context" in formatted
