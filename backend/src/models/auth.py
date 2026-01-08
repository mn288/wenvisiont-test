from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Role(str, Enum):
    ADMIN = "admin"
    ARCHITECT = "architect"
    USER = "user"


class Tenant(BaseModel):
    id: str = Field(..., description="Unique identifier for the tenant (e.g., 'bank-a')")
    name: str = Field(..., description="Display name of the tenant")


class User(BaseModel):
    id: str = Field(..., description="Unique user identifier")
    email: str
    tenant_id: str
    roles: List[Role] = Field(default_factory=lambda: [Role.USER])


class TenantContext(BaseModel):
    """Context object to be shared across the request lifecycle"""

    tenant_id: str
    user_id: Optional[str] = None
    roles: List[Role] = []
