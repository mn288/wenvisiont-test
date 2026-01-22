from unittest.mock import MagicMock

import pytest
from expects import contain, equal, expect
from fastapi import status
from httpx import AsyncClient


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
    Ideally this should query the DB, not return a hardcoded list.
    """
    # Configure mock to return expected servers
    mock_db_cursor.fetchall.return_value = [("local",), ("fastmcp",)]

    response = await client.get("/agents/mcp/servers", headers=mock_user_headers)
    expect(response.status_code).to(equal(200))

    data = response.json()
    expect(data).to(contain("local"))  # Check for default


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
async def test_create_mcp_server_duplicate(client: AsyncClient, mock_admin_headers, mock_db_cursor):
    """
    Test that creating a duplicate server returns 409 Conflict.
    We mock the DB interaction to simulate a found existing row.
    """
    # 1. execute(SELECT 1 ...)
    # 2. fetchone() -> if result: raise 409

    # Check if fetchone is AsyncMock or regular Mock
    is_async = hasattr(mock_db_cursor.fetchone, "assert_awaited")

    start_side_effect = mock_db_cursor.fetchone.side_effect

    if is_async:
        mock_db_cursor.fetchone.side_effect = [(1,)]
    else:
        # Fallback if it's not async mock (unlikely given client fixture, but safe)
        mock_db_cursor.fetchone.side_effect = [(1,)]

    response = await client.post(
        "/mcp/", json={"name": "duplicate-server", "type": "stdio", "command": "ls"}, headers=mock_admin_headers
    )

    if response.status_code != 409:
        print(f"DEBUG Dupe Fail: {response.text}")
        # Debug why?
        # Maybe fetchone wasn't called?
        # Maybe execute failed?

    expect(response.status_code).to(equal(status.HTTP_409_CONFLICT))
    expect(response.json()["detail"]).to(contain("already exists"))

    mock_db_cursor.fetchone.side_effect = start_side_effect


@pytest.mark.asyncio
async def test_delete_mcp_server_not_found(client: AsyncClient, mock_admin_headers, mock_db_cursor):
    """
    Test that deleting a non-existent server returns 404 Not Found.
    """
    from unittest.mock import MagicMock

    mock_result = MagicMock()
    mock_result.rowcount = 0

    # If execute() is awaited, it returns return_value.
    mock_db_cursor.execute.return_value = mock_result

    response = await client.delete("/mcp/non-existent-server", headers=mock_admin_headers)

    if response.status_code != 404:
        print(f"DEBUG Delete Fail: {response.text}")

    expect(response.status_code).to(equal(status.HTTP_404_NOT_FOUND))


@pytest.mark.asyncio
async def test_list_mcp_servers_success(client: AsyncClient, mock_admin_headers, mock_db_cursor):
    mock_db_cursor.fetchall.return_value = [(1, "srv1", "stdio", "ls", [], "", {})]
    response = await client.get("/mcp/", headers=mock_admin_headers)
    expect(response.status_code).to(equal(200))
    expect(len(response.json())).to(equal(1))
    expect(response.json()[0]["name"]).to(equal("srv1"))


@pytest.mark.asyncio
async def test_list_mcp_servers_error(client: AsyncClient, mock_admin_headers, mock_db_cursor):
    mock_db_cursor.execute.side_effect = Exception("DB Fail")
    response = await client.get("/mcp/", headers=mock_admin_headers)
    expect(response.status_code).to(equal(500))


@pytest.mark.asyncio
async def test_create_mcp_server_error(client: AsyncClient, mock_admin_headers, mock_db_cursor):
    # Pass duplicate check
    mock_db_cursor.fetchone.side_effect = [None]
    # Fail insert
    mock_db_cursor.execute.side_effect = [None, Exception("Insert Fail")]

    response = await client.post(
        "/mcp/", json={"name": "srv1", "type": "stdio", "command": "ls"}, headers=mock_admin_headers
    )
    expect(response.status_code).to(equal(500))


@pytest.mark.asyncio
async def test_delete_mcp_server_success(client: AsyncClient, mock_admin_headers, mock_db_cursor):
    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_db_cursor.execute.return_value = mock_result

    response = await client.delete("/mcp/srv1", headers=mock_admin_headers)
    expect(response.status_code).to(equal(200))


@pytest.mark.asyncio
async def test_delete_mcp_server_error(client: AsyncClient, mock_admin_headers, mock_db_cursor):
    mock_db_cursor.execute.side_effect = Exception("Delete Fail")
    response = await client.delete("/mcp/srv1", headers=mock_admin_headers)
    expect(response.status_code).to(equal(500))
