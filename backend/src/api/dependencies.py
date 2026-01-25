from typing import AsyncGenerator

from fastapi import Header, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from api.middleware import get_current_role
from core.database import async_session_maker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to provide a database session."""
    async with async_session_maker() as session:
        yield session


def require_role(required_role: str):
    """
    Dependency to enforce Role-Based Access Control (RBAC).
    Usage: dependencies=[Depends(require_role("ADMIN"))]
    """

    def role_checker(x_role: str = Header("VIEWER", alias="X-Role")):
        # 1. Trust Middleware Context (Best for internal consistency)
        current_role = get_current_role() or x_role.upper()

        # 2. Simple Hierarchy (Expand logic as needed)
        # ADMIN > EDITOR > VIEWER
        hierarchy = {"ADMIN": 3, "EDITOR": 2, "VIEWER": 1}

        current_level = hierarchy.get(current_role, 0)
        required_level = hierarchy.get(required_role.upper(), 99)

        if current_level < required_level:
            raise HTTPException(
                status_code=403, detail=f"Permission Denied: Required {required_role}, got {current_role}"
            )
        return current_role

    return role_checker
