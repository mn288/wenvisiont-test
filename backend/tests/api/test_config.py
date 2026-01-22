import pytest
from expects import equal, expect
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_config_success(client: AsyncClient, mock_db_cursor):
    # Mock DB return
    mock_db_cursor.fetchone.return_value = ("test_key", {"foo": "bar"})

    response = await client.get("/configurations/test_key")
    expect(response.status_code).to(equal(200))
    data = response.json()
    expect(data["key"]).to(equal("test_key"))
    expect(data["value"]).to(equal({"foo": "bar"}))


@pytest.mark.asyncio
async def test_get_config_not_found(client: AsyncClient, mock_db_cursor):
    mock_db_cursor.fetchone.return_value = None

    response = await client.get("/configurations/unknown_key")
    expect(response.status_code).to(equal(404))


@pytest.mark.asyncio
async def test_create_or_update_config(client: AsyncClient, mock_db_cursor):
    payload = {"key": "new_key", "value": {"a": 1}}

    response = await client.post("/configurations/", json=payload)
    expect(response.status_code).to(equal(200))
    data = response.json()
    expect(data["key"]).to(equal("new_key"))

    # Verify INSERT executed
    expect(mock_db_cursor.execute.called).to(equal(True))


@pytest.mark.asyncio
async def test_delete_config(client: AsyncClient, mock_db_cursor):
    response = await client.delete("/configurations/delete_me")
    expect(response.status_code).to(equal(200))
    expect(mock_db_cursor.execute.called).to(equal(True))
