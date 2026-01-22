from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware import TenantMiddleware


def configure_middleware(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(TenantMiddleware)
