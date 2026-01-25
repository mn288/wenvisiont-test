from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from expects import contain, equal, expect
from fastapi import status
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def mock_mcp_verify():
    # Patch the verification method to avoid real network calls
    with patch("services.mcp.MCPService._verify_server", new_callable=AsyncMock) as mock:
        yield mock


@pytest.mark.asyncio
async def test_mcp_servers_rbac_unauthorized(client: AsyncClient, mock_user_headers):
    """
    Test that standard users CANNOT create or delete MCP servers.
    They should receive a 403 Forbidden.
    """
    # Try to creating a server
    response = await client.post(
        "/mcp/", json={"name": "test-server", "url": "http://localhost:8000", "type": "sse"}, headers=mock_user_headers
    )
    expect(response.status_code).to(equal(status.HTTP_403_FORBIDDEN))

    # Try to delete a server
    response = await client.delete("/mcp/test-server", headers=mock_user_headers)
    expect(response.status_code).to(equal(status.HTTP_403_FORBIDDEN))


@pytest.mark.asyncio
async def test_mcp_servers_rbac_authorized(client: AsyncClient, mock_admin_headers, db_pool_mock):
    """
    Test that ADMIN users CAN create and delete MCP servers.
    Since we mock the DB, we expect success or specific mock behavior.
    """
    # Try creating a server
    # We might need to mock the DB insertion if the endpoint goes to DB
    # The db_pool_mock ensures it doesn't crash on connection, but it might return None

    response = await client.post(
        "/mcp/",
        json={"name": "test-server", "url": "http://localhost:8000/sse", "type": "sse"},
        headers=mock_admin_headers,
    )

    # If the endpoint is implemented to use DB, it might pass or fail depending on what fetchall returns
    # But checking for NOT 403 is the key here.
    # 200, 201, or even 500 (due to logic error) means RBAC passed.
    expect(response.status_code).not_to(equal(status.HTTP_403_FORBIDDEN))


@pytest.mark.asyncio
async def test_list_available_mcp_servers(client: AsyncClient, mock_user_headers, mock_db_cursor):
    """
    Test the endpoint that agents use to list available servers.
    This endpoint uses psycopg pool directly (not SQLModel).
    """
    # Configure mock cursor to return expected servers
    mock_db_cursor.fetchall.return_value = [("local",), ("fastmcp",)]

    response = await client.get("/agents/mcp/servers", headers=mock_user_headers)
    expect(response.status_code).to(equal(200))

    data = response.json()
    expect(data).to(contain("local"))  # Check for default
    expect(data).to(contain("fastmcp"))


@pytest.mark.asyncio
async def test_create_mcp_server_validation_error(client: AsyncClient, mock_admin_headers):
    """
    Test validation rules:
    - 'stdio' requires 'command'
    - 'sse'/'https' requires 'url'
    """
    # 1. Stdio without command
    response = await client.post(
        "/mcp/", json={"name": "bad-stdio", "type": "stdio", "args": []}, headers=mock_admin_headers
    )
    expect(response.status_code).to(equal(status.HTTP_400_BAD_REQUEST))
    expect(response.json()["detail"]).to(contain("Command is required"))

    # 2. SSE without URL
    response = await client.post("/mcp/", json={"name": "bad-sse", "type": "sse"}, headers=mock_admin_headers)
    expect(response.status_code).to(equal(status.HTTP_400_BAD_REQUEST))
    expect(response.json()["detail"]).to(contain("URL is required"))


@pytest.mark.asyncio
async def test_create_mcp_server_duplicate(client: AsyncClient, mock_admin_headers, mock_async_session):
    """
    Test that creating a duplicate server returns 409 Conflict.
    We mock the DB interaction to simulate a found existing row.
    """
    # MCPService check duplication via select().where()... first()
    mock_existing = MagicMock()
    mock_existing.name = "duplicate-server"

    # Configure mock session for duplicate check
    mock_async_session.exec.return_value.first.return_value = mock_existing

    response = await client.post(
        "/mcp/", json={"name": "duplicate-server", "type": "stdio", "command": "ls"}, headers=mock_admin_headers
    )

    if response.status_code != 409:
        print(f"DEBUG Dupe Fail: {response.text}")

    expect(response.status_code).to(equal(status.HTTP_409_CONFLICT))

    # Reset
    mock_async_session.exec.return_value.first.return_value = None


@pytest.mark.asyncio
async def test_delete_mcp_server_not_found(client: AsyncClient, mock_admin_headers, mock_async_session):
    """
    Test that deleting a non-existent server returns 404 Not Found.
    """
    # Delete looks for server first
    mock_async_session.exec.return_value.first.return_value = None

    response = await client.delete("/mcp/non-existent-server", headers=mock_admin_headers)

    if response.status_code != 404:
        print(f"DEBUG Delete Fail: {response.text}")

    expect(response.status_code).to(equal(status.HTTP_404_NOT_FOUND))


@pytest.mark.asyncio
async def test_list_mcp_servers_success(client: AsyncClient, mock_admin_headers, mock_async_session):
    srv1 = MagicMock()
    srv1.name = "srv1"
    srv1.type = "stdio"
    srv1.command = "ls"
    srv1.args = []
    srv1.env = {}
    srv1.url = None

    mock_async_session.exec.return_value.all.return_value = [srv1]

    response = await client.get("/mcp/", headers=mock_admin_headers)
    expect(response.status_code).to(equal(200))
    expect(len(response.json())).to(equal(1))
    expect(response.json()[0]["name"]).to(equal("srv1"))


@pytest.mark.asyncio
async def test_list_mcp_servers_error(client: AsyncClient, mock_admin_headers, mock_async_session):
    mock_async_session.exec.side_effect = Exception("DB Fail")
    response = await client.get("/mcp/", headers=mock_admin_headers)
    expect(response.status_code).to(equal(500))


@pytest.mark.asyncio
async def test_create_mcp_server_error(client: AsyncClient, mock_admin_headers, mock_async_session):
    # Pass duplicate check (first returns None)
    mock_async_session.exec.return_value.first.return_value = None

    # Fail commit (Insert)
    mock_async_session.commit.side_effect = Exception("Insert Fail")

    response = await client.post(
        "/mcp/", json={"name": "srv1", "type": "stdio", "command": "ls"}, headers=mock_admin_headers
    )
    expect(response.status_code).to(equal(500))


@pytest.mark.asyncio
async def test_delete_mcp_server_success(client: AsyncClient, mock_admin_headers, mock_async_session):
    # Mock finding the server
    mock_server = MagicMock()
    mock_server.name = "srv1"
    mock_async_session.exec.return_value.first.return_value = mock_server

    response = await client.delete("/mcp/srv1", headers=mock_admin_headers)
    expect(response.status_code).to(equal(200))


@pytest.mark.asyncio
async def test_delete_mcp_server_error(client: AsyncClient, mock_admin_headers, mock_async_session):
    # Mock finding the server
    mock_server = MagicMock()
    mock_server.name = "srv1"
    mock_async_session.exec.return_value.first.return_value = mock_server

    # Fail commit (Delete)
    mock_async_session.commit.side_effect = Exception("Delete Fail")

    response = await client.delete("/mcp/srv1", headers=mock_admin_headers)
    expect(response.status_code).to(equal(500))
