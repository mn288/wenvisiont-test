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
        # 1. Extract Tenant ID
        tenant_id = request.headers.get("X-Tenant-ID")

        # 2. Development Fallback (Optional, can be removed in Prod)
        if not tenant_id:
            # Check if we are in a dev environment or if strict mode is disabled
            # For now, we default to 'default-tenant' to not break existing calls
            # In a real strict mode, we would return 403 here.
            tenant_id = "default-tenant"

        # 3. Set Context
        # We store just the ID for now, but could store a full model
        token = tenant_context.set(tenant_id)

        # 3.1 Extract Role
        # For local development/industrialization phase, we default to ADMIN (Superadmin)
        user_role = request.headers.get("X-Role", "ADMIN").upper()
        role_token = role_context.set(user_role)

        # 3.2 Extract User ID (New for Observability)
        # Prioritize Header (X-User-ID) > Query Param (user_id) > Anonymous
        user_id = request.headers.get("X-User-ID")
        if not user_id:
            user_id = request.query_params.get("user_id")
        
        if not user_id:
            user_id = "anonymous-user"

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
