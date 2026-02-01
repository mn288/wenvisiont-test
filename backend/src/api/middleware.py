import contextvars

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# Global context variable to store tenant information
# verifying that we can access this from anywhere in the app
tenant_context = contextvars.ContextVar("tenant_context", default=None)
role_context = contextvars.ContextVar("role_context", default="VIEWER")  # Default role
user_id_context = contextvars.ContextVar("user_id_context", default=None)


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 1. Identity Source of Truth: request.state.user (from Auth Middleware)
        # If not present (e.g. public endpoint), we drift to defaults or anonymous
        user_identity = getattr(request.state, "user", {})

        # 2. Extract Tenant ID
        # Prefer Identity Tenant > Header > Default
        tenant_id = user_identity.get("tenant_id") or request.headers.get("X-Tenant-ID")

        # Development Fallback
        if not tenant_id:
            tenant_id = "default-tenant"

        # 3. Set Context
        token = tenant_context.set(tenant_id)

        # 3.1 Extract Role
        # Prefer Identity Role > Header > Default
        # user_identity["roles"] might be a list or single string
        # 3.1 Extract Role
        roles = user_identity.get("roles")
        user_role = None

        if roles:
            if isinstance(roles, list):
                user_role = roles[0] if roles else None
            else:
                user_role = str(roles)

        if not user_role:
            user_role = request.headers.get("X-Role", "VIEWER")

        # Normalize
        user_role = user_role.upper()
        role_token = role_context.set(user_role)

        # 3.2 Extract User ID
        user_id = user_identity.get("sub") or user_identity.get("user_id") or request.headers.get("X-User-ID")

        if not user_id:
            user_id = request.query_params.get("user_id") or "anonymous-user"

        user_id_token = user_id_context.set(user_id)

        try:
            response = await call_next(request)
            return response
        finally:
            # 4. Clean up
            tenant_context.reset(token)
            role_context.reset(role_token)
            user_id_context.reset(user_id_token)


def get_current_tenant_id() -> str:
    """Helper to get current tenant ID from context"""
    return tenant_context.get() or "default-tenant"


def get_current_role() -> str:
    """Helper to get current user role from context"""
    return role_context.get()


def get_current_user_id() -> str:
    """Helper to get current user ID from context"""
    return user_id_context.get() or "anonymous-user"
