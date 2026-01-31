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


class Citation(BaseModel):
    """A strictly typed citation for source attribution."""

    source_id: str = Field(..., description="Unique ID of the source (e.g. filename, url)")
    uri: str = Field(..., description="URI or path to the source")
    title: Optional[str] = Field(None, description="Human readable title")
    snippet: Optional[str] = Field(None, description="Relevant content snippet")
    score: Optional[float] = Field(None, description="Relevance score if applicable")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


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
    assigned_to: str = Field(default="unknown", description="Name of the agent that performed the task")
    artifacts: List[Dict[str, Any]] = Field(default_factory=list, description="Structured artifacts (e.g. usage stats)")
    citations: List[Citation] = Field(default_factory=list, description="Source citations backing this result")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata (tokens, model, etc.)")
    timestamp: datetime = Field(default_factory=datetime.now)


def merge_dict(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    return {**a, **b}


class GraphState(TypedDict):
    """The State of the Brain (LangGraph)."""

    # 1. Input
    input_request: str
    # Strict conversation history with add_messages reducer
    # This handles the "rolling window" naturally via checkpointer features if needed,
    # or we can trust the list to grow and prune it in a node or util.
    messages: Annotated[List[Any], operator.add]

    # 2. Strict Task Management
    # Tasks and Results log. using append (operator.add)
    tasks: Annotated[List[Dict[str, Any]], operator.add]
    results: Annotated[List[Dict[str, Any]], operator.add]

    # 2.5 Citations (Aggregated)
    citations: Annotated[List[Citation], operator.add]

    # 3. Flow Control
    next_step: Optional[List[str]]

    # 3.5. Recursive Planning (Plan-and-Execute)
    # The active plan of future steps.
    plan: Annotated[List[str], lambda x, y: y]  # Overwrite reducer

    # 4. Global Context (The "Knowledge")
    global_state: Annotated[Dict[str, Any], merge_dict]

    # 5. Final Output
    final_response: Optional[str]
    errors: Annotated[List[str], operator.add]

    # 6. Safety
    retry_count: int
    last_agent: Optional[str]

    # 7. Legacy / Deprecated (Keep for compatibility if code references them, or remove if safe)
    # We will remove 'conversation_buffer' and 'long_term_summary' as they are manual reinventions.
    # We keep 'context' as a simple string reducer for summaries if needed
    context: Annotated[Optional[str], reduce_str]
