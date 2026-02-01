"""
Authentication Middleware for GCP Identity-Aware Proxy (IAP).

This module provides:
- IAPMiddleware: Production JWT validation for GCP IAP
- MockOIDCMiddleware: Local development fallback with mock user

The middleware automatically falls back to mock auth in DEV mode or when
IAP_VERIFY_ENABLED is False, ensuring local development works without GCP.
"""

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from core.config import Environment, settings

logger = logging.getLogger(__name__)

# Public paths that bypass authentication
PUBLIC_PATHS = {"/health", "/ready", "/docs", "/openapi.json", "/redoc"}


class IAPMiddleware(BaseHTTPMiddleware):
    """
    Validates GCP Identity-Aware Proxy JWT tokens.

    The `x-goog-iap-jwt-assertion` header is injected by the GCP Load Balancer
    when IAP is enabled. This middleware:
    1. Extracts and verifies the JWT signature using Google's public keys
    2. Extracts user identity (sub, email) and attaches to request.state.user
    3. Returns 401 if validation fails in production

    In DEV mode or when IAP_VERIFY_ENABLED=False, falls back to MockOIDCMiddleware.
    """

    def __init__(self, app):
        super().__init__(app)
        self._request = None  # Lazy-loaded Google Auth transport

    def _get_google_request(self):
        """Lazy-load Google Auth transport to avoid import errors in dev."""
        if self._request is None:
            from google.auth.transport import requests as google_requests

            self._request = google_requests.Request()
        return self._request

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip auth for public paths
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # Check if IAP verification is enabled
        if not settings.IAP_VERIFY_ENABLED or settings.ENV == Environment.DEV:
            # Fallback to mock auth for local development
            return await self._mock_dispatch(request, call_next)

        # Get the IAP JWT assertion header
        iap_jwt = request.headers.get("x-goog-iap-jwt-assertion")

        if not iap_jwt:
            logger.warning("Missing x-goog-iap-jwt-assertion header")
            return Response(
                content='{"detail": "Missing IAP authentication"}',
                status_code=401,
                media_type="application/json",
            )

        try:
            # Verify the JWT using Google's library
            from google.oauth2 import id_token

            # Audience is the OAuth Client ID (auto-set by Google-managed client)
            audience = settings.IAP_AUDIENCE
            if not audience:
                logger.error("IAP_AUDIENCE not configured")
                return Response(
                    content='{"detail": "IAP configuration error"}',
                    status_code=500,
                    media_type="application/json",
                )

            # Verify token and extract claims
            claims = id_token.verify_token(iap_jwt, self._get_google_request(), audience=audience)

            # Attach user info to request state
            request.state.user = {
                "sub": claims.get("sub"),
                "email": claims.get("email"),
                "hd": claims.get("hd"),  # Hosted domain (for org restriction)
            }
            logger.debug(f"IAP auth successful for user: {claims.get('email')}")

        except ValueError as e:
            logger.warning(f"IAP JWT validation failed: {e}")
            return Response(
                content='{"detail": "Invalid IAP token"}',
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)

    async def _mock_dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Inject mock user for local development."""
        if not hasattr(request.state, "user"):
            request.state.user = {
                "sub": "mock-developer-id",
                "email": "dev@wenvision.com",
                "roles": ["ADMIN"],
            }
            logger.debug("Mock auth: Injected dev user")
        return await call_next(request)


# Alias for backward compatibility
OIDCMiddleware = IAPMiddleware


class MockOIDCMiddleware(BaseHTTPMiddleware):
    """
    Dev Middleware that injects a Mock User identity if no token provided.
    Use this explicitly for local development or testing without IAP.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip auth for public paths
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # If X-Role header is explicitly provided, skip mock injection
        # This allows tests to control roles via headers
        if request.headers.get("X-Role"):
            return await call_next(request)

        # Inject Mock User if not present
        if not hasattr(request.state, "user"):
            request.state.user = {
                "sub": "mock-developer-id",
                "email": "dev@wenvision.com",
                "roles": ["ADMIN"],
            }

        return await call_next(request)
