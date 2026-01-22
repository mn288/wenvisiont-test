from datetime import datetime
from typing import List, Optional

from sqlmodel import ARRAY, JSON, Column, Field, SQLModel, String


class MCPServer(SQLModel, table=True):
    __tablename__ = "mcp_servers"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    type: str = Field(
        description="stdio | sse | https"
    )  # Pattern validation can be done in Pydantic schema if needed, but for DB model we keep it simple or use sa_column_args
    command: Optional[str] = None
    args: Optional[List[str]] = Field(default=None, sa_column=Column(ARRAY(String)))
    url: Optional[str] = None
    env: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.now)


# Keep Pydantic models for API if strictly needed, or alias SQLModel
MCPServerConfig = MCPServer


class MCPServerCreate(SQLModel):
    name: str
    type: str
    command: Optional[str] = None
    args: Optional[List[str]] = []
    url: Optional[str] = None
    env: Optional[dict] = {}
