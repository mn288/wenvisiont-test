from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID, uuid4

from sqlmodel import JSON, Column, Field, SQLModel


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
