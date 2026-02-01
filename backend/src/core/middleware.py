from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import MockOIDCMiddleware, OIDCMiddleware
from api.middleware import TenantMiddleware
from core.config import settings


def configure_middleware(app: FastAPI):
    # Middleware is executed in reverse order of addition (Last added = First execution)

    # 3. Tenant Context (Deepest)
    app.add_middleware(TenantMiddleware)

    # 2. Authentication (Injects Identity for TenantMiddleware)
    if settings.is_prod:
        app.add_middleware(OIDCMiddleware)
    else:
        app.add_middleware(MockOIDCMiddleware)

    # 1. CORS (Outermost - Handles Preflight)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
