from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class OIDCMiddleware(BaseHTTPMiddleware):
    """
    Validates OIDC JWT Tokens.
    In a real implementation, this would use PyJWT or similar to verify signature against JWKS.
    For this Industrialization POC, we implement the structure but placeholder verification.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip Auth for Health Checks and Docs
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            # In strict mode, we would raise 401.
            # raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
            # For now, we log validation failure but might proceed if configured to allowing anonymous in specific cases
            pass

        # token = auth_header.split(" ")[1] if auth_header else None

        # TODO: Implement Real JWT Validation
        # try:
        #     payload = jwt.decode(token, settings.OIDC_PUBLIC_KEY, algorithms=["RS256"], audience=settings.OIDC_AUDIENCE)
        #     request.state.user = payload
        # except Exception as e:
        #      raise HTTPException(status_code=401, detail="Invalid Token")

        return await call_next(request)


class MockOIDCMiddleware(BaseHTTPMiddleware):
    """
    Dev Middleware that injects a Mock User identity if no token provided.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Inject Mock User if not present
        if not request.headers.get("X-User-ID"):
            # We treat this as a mutation of the request for downstream consumption
            # But middleware request object is immutable-ish for headers.
            # Standard pattern is using scope or state.
            request.state.user = {"sub": "mock-developer-id", "email": "dev@wenvision.com", "roles": ["ADMIN"]}

        return await call_next(request)
