from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlmodel import JSON, Column, Field, SQLModel

# -------------------------------------------------------------------------
# Shared Schemas (Moved from registry.py)
# -------------------------------------------------------------------------

class AgentConfig(BaseModel):
    role: str
    goal: str
    backstory: str
    verbose: bool = True
    allow_delegation: bool = False
    tools: List[str] = Field(default_factory=list)
    mcp_servers: List[str] = Field(default_factory=list)
    files_access: bool = False
    s3_access: bool = False
    # CrewAI 2025 parameters
    max_iter: int = 1
    max_retry_limit: int = 1
    max_execution_time: Optional[int] = 30
    respect_context_window: bool = True
    inject_date: bool = True
    # DyLAN-style dynamic agent selection (arXiv:2310.02170)
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Agent importance weight for routing")
    task_domains: List[str] = Field(default_factory=list, description="Domain keywords e.g. ['code', 'research', 'analysis']")
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="Historical task success rate")
    use_reflection: bool = Field(default=False, description="Enable self-correction/reflection step")
    # MetaGPT-style SOP (arXiv:2308.00352)
    sop: Optional[str] = Field(default=None, description="Standard Operating Procedure the agent must follow")


class TaskConfig(BaseModel):
    description: str
    expected_output: str
    async_execution: bool = False


class NodeConfig(BaseModel):
    name: str = Field(..., description="Graph Node Name")
    display_name: str = Field(..., description="Supervisor Prompt Name")
    description: str = Field(..., description="Supervisor Prompt Description")
    output_state_key: str = Field("crew_output", description="State key to update with result")
    agent: AgentConfig
    task: TaskConfig


# -------------------------------------------------------------------------
# Database Models
# -------------------------------------------------------------------------

class SuperAgent(SQLModel, table=True):
    """
    Database model for Agents.
    Replaces file-system YAML storage for better industrialization and stateless deployment.
    """

    __tablename__ = "superagents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True, description="Snake_case unique identifier")

    # Store the full NodeConfig structure as JSON
    # We use sa_column=Column(JSON) to ensure it maps correctly to JSONB in Postgres
    config: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
