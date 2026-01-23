"""
Skill model for Voyager persistent skill library.

Stores successful agent solutions as embeddings for retrieval-augmented generation.
Uses pgvector for similarity search.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class Skill(SQLModel, table=True):
    """
    A reusable skill learned by an agent.
    
    Based on Voyager (arXiv:2305.16291) concept of persistent skill library.
    """

    __tablename__ = "skills"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Agent context
    agent_role: str = Field(index=True, description="Role of the agent that created this skill")
    
    # Task description (searchable)
    task_description: str = Field(sa_column=Column(Text), description="Original task that was solved")
    
    # Solution (the skill itself)
    solution_code: str = Field(sa_column=Column(Text), description="Code or solution that worked")
    
    # Vector embedding for similarity search (OpenAI ada-002 = 1536 dims)
    embedding: Optional[List[float]] = Field(
        default=None,
        sa_column=Column(Vector(1536)),
        description="Vector embedding of task_description for similarity search"
    )
    
    # Metadata
    usage_count: int = Field(default=0, description="How many times this skill was retrieved")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
