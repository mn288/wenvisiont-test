"""Unit tests for IAP authentication middleware."""

from unittest.mock import patch

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from api.auth import IAPMiddleware, MockOIDCMiddleware
from core.config import Environment


# Create test app with middleware
def create_test_app(middleware_class: type[BaseHTTPMiddleware]) -> FastAPI:
    app = FastAPI()
    app.add_middleware(middleware_class)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/protected")
    async def protected(request: Request):
        user = getattr(request.state, "user", None)
        return {"user": user}

    return app


class TestMockOIDCMiddleware:
    """Tests for the mock authentication middleware (local dev)."""

    def test_public_path_bypasses_auth(self):
        """Health check should not inject user."""
        app = create_test_app(MockOIDCMiddleware)
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_protected_path_injects_mock_user(self):
        """Protected endpoints should get mock user injected."""
        app = create_test_app(MockOIDCMiddleware)
        client = TestClient(app)
        response = client.get("/protected")
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "dev@wenvision.com"
        assert data["user"]["sub"] == "mock-developer-id"


class TestIAPMiddleware:
    """Tests for the IAP JWT validation middleware."""

    def test_dev_mode_uses_mock_auth(self):
        """DEV environment should use mock authentication."""
        with patch("api.auth.settings") as mock_settings:
            mock_settings.ENV = Environment.DEV
            mock_settings.IAP_VERIFY_ENABLED = True

            app = create_test_app(IAPMiddleware)
            client = TestClient(app)
            response = client.get("/protected")
            assert response.status_code == 200
            data = response.json()
            assert data["user"]["email"] == "dev@wenvision.com"

    def test_iap_disabled_uses_mock_auth(self):
        """IAP_VERIFY_ENABLED=False should use mock authentication."""
        with patch("api.auth.settings") as mock_settings:
            mock_settings.ENV = Environment.PROD
            mock_settings.IAP_VERIFY_ENABLED = False

            app = create_test_app(IAPMiddleware)
            client = TestClient(app)
            response = client.get("/protected")
            assert response.status_code == 200
            data = response.json()
            assert data["user"]["email"] == "dev@wenvision.com"

    def test_missing_jwt_returns_401(self):
        """Missing IAP JWT in production should return 401."""
        with patch("api.auth.settings") as mock_settings:
            mock_settings.ENV = Environment.PROD
            mock_settings.IAP_VERIFY_ENABLED = True

            app = create_test_app(IAPMiddleware)
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/protected")
            assert response.status_code == 401
            assert "Missing IAP authentication" in response.json()["detail"]

    def test_valid_jwt_extracts_user(self):
        """Valid IAP JWT should extract user claims."""
        with (
            patch("api.auth.settings") as mock_settings,
            patch("google.oauth2.id_token.verify_token") as mock_verify,
        ):
            mock_settings.ENV = Environment.PROD
            mock_settings.IAP_VERIFY_ENABLED = True
            mock_settings.IAP_AUDIENCE = "test-audience"

            mock_verify.return_value = {
                "sub": "user-123",
                "email": "test@example.com",
                "hd": "example.com",
            }

            app = create_test_app(IAPMiddleware)
            client = TestClient(app)
            response = client.get(
                "/protected",
                headers={"x-goog-iap-jwt-assertion": "valid-jwt-token"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["user"]["email"] == "test@example.com"
            assert data["user"]["sub"] == "user-123"

    def test_invalid_jwt_returns_401(self):
        """Invalid IAP JWT should return 401."""
        with (
            patch("api.auth.settings") as mock_settings,
            patch("google.oauth2.id_token.verify_token") as mock_verify,
        ):
            mock_settings.ENV = Environment.PROD
            mock_settings.IAP_VERIFY_ENABLED = True
            mock_settings.IAP_AUDIENCE = "test-audience"

            mock_verify.side_effect = ValueError("Token expired")

            app = create_test_app(IAPMiddleware)
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get(
                "/protected",
                headers={"x-goog-iap-jwt-assertion": "expired-jwt-token"},
            )
            assert response.status_code == 401
            assert "Invalid IAP token" in response.json()["detail"]

    def test_missing_audience_returns_500(self):
        """Missing IAP_AUDIENCE in production should return 500."""
        with patch("api.auth.settings") as mock_settings:
            mock_settings.ENV = Environment.PROD
            mock_settings.IAP_VERIFY_ENABLED = True
            mock_settings.IAP_AUDIENCE = None

            app = create_test_app(IAPMiddleware)
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get(
                "/protected",
                headers={"x-goog-iap-jwt-assertion": "some-jwt-token"},
            )
            assert response.status_code == 500
            assert "IAP configuration error" in response.json()["detail"]

    def test_public_paths_bypass_iap(self):
        """Public paths should bypass IAP validation entirely."""
        app = create_test_app(IAPMiddleware)
        client = TestClient(app)

        # Health check should always work
        response = client.get("/health")
        assert response.status_code == 200
