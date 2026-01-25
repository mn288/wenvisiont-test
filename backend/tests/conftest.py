"""
TESTING GUIDE: Using this `conftest.py`
---------------------------------------

This module provides global fixtures to streamline testing for Backend API, DB, and logic.
It uses `pytest-asyncio` for async support and `unittest.mock` for dependency isolation.

Key Fixtures:

1. `client` (AsyncClient):
   - Use this to make HTTP requests to the FastAPI app.
   - Example: `response = await client.get("/health")`

2. `db_pool_mock`, `mock_db_connection`, `mock_db_cursor`:
   - These fixtures automatically patch the database pool to prevent real connections.
   - Use `mock_db_cursor` to define what the DB should return for a query.
   - Example (Mocking a SELECT):
     ```python
     mock_db_cursor.fetchall.return_value = [("row1_col1",), ("row2_col1",)]
     mock_db_cursor.fetchone.return_value = ("single_row",)
     ```
   - Example (Verifying an INSERT):
     ```python
     expect(mock_db_cursor.execute.called).to(equal(True))
     # Check arguments
     args, _ = mock_db_cursor.execute.call_args
     expect(args[0]).to(contain("INSERT INTO"))
     ```

3. `mock_admin_headers` & `mock_user_headers`:
   - Pre-configured headers for RBAC testing.
   - `ADMIN` has full access; `USER` has restricted access.
   - Usage: `client.post("/admin-only", headers=mock_admin_headers)`

Common Patterns:

- **Patching Imports**:
  If a module under test imports `pool` directly (e.g., `from core.database import pool`),
  the `db_pool_mock` fixture patches it in common locations (`api.main`, `brain.registry`).
  If you encounter `psycopg_pool.PoolClosed` errors, ensure the module you are testing
  is included in the `patch` list within the `db_pool_mock` fixture.

- **Mocking Classes**:
  For external services (like LLMs or S3), use `unittest.mock.patch` within specific test files
  or create new fixtures here if used widely.
  Be careful with Pydantic validation when mocking classes used in Pydantic models;
  you may need to patch the class itself (e.g. `patch("brain.registry.Agent")`).
"""

import asyncio

# We mock the app import to avoid aggressive lifespan startup if needed,
# but usually importing the app object is fine if we patch the pool before usage.
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

os.environ["WORKSPACE_ROOT"] = "/tmp/test_workspace"
from api.main import app as original_app


@pytest_asyncio.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create a fresh event loop for the session scope."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
def mock_db_cursor():
    """
    Returns a mock cursor that allows configuring return values for queries.
    """
    cursor = AsyncMock()
    cursor.fetchall.return_value = []
    cursor.fetchone.return_value = None
    return cursor


@pytest_asyncio.fixture
def mock_db_connection(mock_db_cursor):
    """
    Returns a mock connection that yields the mock cursor.
    """
    connection = AsyncMock()
    # 'async with conn.cursor() as cur'
    # conn.cursor() returns a ContextManager.
    # If connection is AsyncMock, conn.cursor is an AsyncMock. calling it returns a coroutine.
    # But psycopg cursor() is sync.
    # We need conn.cursor to be a MagicMock (sync) that returns an AsyncMock (the cursor).

    # Force cursor() to be a non-async callable
    connection.cursor = MagicMock(return_value=mock_db_cursor)

    # Configure the cursor (AsyncMock) to allow 'async with'
    mock_db_cursor.__aenter__.return_value = mock_db_cursor
    mock_db_cursor.__aexit__.return_value = None

    return connection


@pytest_asyncio.fixture(scope="function", autouse=True)
async def db_pool_mock(mock_db_connection):
    """
    Patch the `pool` object in `core.database` (and `api.main` if imported there)
    to prevent real DB connections.
    """
    mock_pool = MagicMock()

    # Pool yields connection: 'async with pool.connection() as conn'
    mock_pool.connection.return_value.__aenter__.return_value = mock_db_connection

    # We patch strictly where it is used.
    # Since `api.main` imports `pool` from `core.database`, we might need to patch both
    # or patch the source `core.database.pool`.

    with (
        patch("core.database.pool", new=mock_pool),
        # patch("api.main.pool", new=mock_pool), # Removed from main
        patch("api.v1.endpoints.execution.pool", new=mock_pool),
        patch("api.v1.endpoints.history.pool", new=mock_pool),
        patch("api.v1.endpoints.config_endpoints.pool", new=mock_pool),
        patch("api.v1.endpoints.stats.pool", new=mock_pool),
        patch("core.lifespan.pool", new=mock_pool),
        patch("brain.registry.pool", new=mock_pool),
        patch("services.graph_service.pool", new=mock_pool),
    ):
        yield mock_pool


@pytest_asyncio.fixture(scope="function")
async def app(db_pool_mock) -> FastAPI:
    """Return the FastAPI app with mocked dependencies."""
    return original_app


@pytest_asyncio.fixture(scope="function")
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Return an async HTTP client for the app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture(scope="function", autouse=True)
async def mock_async_session(mock_db_cursor):
    """
    Patch `async_session_maker` for SQLModel based services.
    This ensures that `async with async_session_maker() as session` works and returns a mock session.
    """
    # Create a Mock Session
    mock_session = AsyncMock()
    mock_session.exec = AsyncMock()

    # exec returns a Result object which has .all(), .first()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_result.first.return_value = None

    mock_session.exec.return_value = mock_result
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.delete = AsyncMock()

    # The session_maker is a callable that returns an async context manager
    # async with async_session_maker() as session:

    # We need a MagicMock that returns an AsyncContextManager
    mock_maker = MagicMock()
    mock_maker.return_value.__aenter__.return_value = mock_session
    mock_maker.return_value.__aexit__.return_value = None

    with (
        patch("core.database.async_session_maker", new=mock_maker),
        patch("services.mcp.async_session_maker", new=mock_maker),
        patch("api.dependencies.async_session_maker", new=mock_maker),  # For get_session dependency
    ):
        yield mock_session


@pytest_asyncio.fixture
def mock_admin_headers():
    """Return headers for an ADMIN user."""
    return {"X-Tenant-ID": "default-tenant", "X-Role": "ADMIN", "X-User-ID": "test-admin"}


@pytest_asyncio.fixture
def mock_user_headers():
    """Return headers for a standard USER."""
    return {"X-Tenant-ID": "default-tenant", "X-Role": "USER", "X-User-ID": "test-user"}
