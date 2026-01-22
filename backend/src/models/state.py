import operator
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from pydantic import BaseModel, Field


def reduce_str(a: Optional[str], b: Optional[str]) -> str:
    """Combine strings with a newline separator."""
    if not a:
        return b or ""
    if not b:
        return a
    return f"{a}\n\n{b}"


class AgentTask(BaseModel):
    """A strictly typed task allocated to an agent."""

    id: str = Field(..., description="Unique ID of the task")
    type: str = Field(..., description="Type of task: 'crew' or 'tool'")
    name: str = Field(..., description="Name of the agent or tool")  # e.g. "researcher" or "search_web"
    input_data: Any = Field(..., description="Input payload for the task")
    status: str = Field(default="pending", description="pending, running, completed, failed")
    created_at: datetime = Field(default_factory=datetime.now)
    assigned_to: str = Field(..., description="Display name of the agent")


class AgentResult(BaseModel):
    """The result of an executed task."""

    task_id: str = Field(..., description="ID of the task this result belongs to")
    summary: str = Field(..., description="Concise summary of the result")
    raw_output: str = Field(..., description="Full output from the agent/tool")
    artifacts: List[Dict[str, Any]] = Field(default_factory=list, description="Structured artifacts (e.g. usage stats)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata (tokens, model, etc.)")
    timestamp: datetime = Field(default_factory=datetime.now)


class GraphState(TypedDict):
    """The State of the Brain (LangGraph)."""

    # 1. Input
    input_request: str
    messages: Annotated[List[Any], operator.add]  # Strict conversation history

    # 2. Strict Task Management
    # We treat 'tasks' as a log of all assignments.
    # We treat 'results' as a log of all completions.
    tasks: Annotated[List[Dict[str, Any]], operator.add]  # Serialized AgentTask
    results: Annotated[List[Dict[str, Any]], operator.add]  # Serialized AgentResult

    # 3. Flow Control
    # 'next_step' determines where the graph goes next.
    next_step: Optional[List[str]]

    # 4. Global Context (Accumulated findings for the LLM)
    # Replaces loose 'intermediate_findings', 'research_output'
    context: Annotated[Optional[str], reduce_str]

    # 5. Final Output
    final_response: Optional[str]
    errors: Annotated[List[str], operator.add]

    # 6. Legacy / Transition (Keep temporarily to avoid massive breakage during refactor)
    # We will mark these as deprecated
    tool_call: Optional[Dict[str, Any]]  # Deprecated: Use tasks
    structured_history: Annotated[List[Dict[str, str]], operator.add]  # Deprecated: Use results
