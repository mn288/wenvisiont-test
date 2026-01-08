from unittest.mock import patch

import pytest
from expects import equal, expect, have_keys
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_stats_success(client: AsyncClient, mock_user_headers, mock_db_cursor):
    # Mock DB total invocations
    mock_db_cursor.fetchone.return_value = (42,)

    # Mock AgentRegistry
    with patch("api.v1.endpoints.stats.AgentRegistry") as MockRegistry:
        MockRegistry.return_value.get_all.return_value = ["a1", "a2", "a3"]

        response = await client.get("/stats/", headers=mock_user_headers)
        expect(response.status_code).to(equal(200))
        data = response.json()

        expect(data).to(have_keys("compliance_score", "total_invocations", "active_agents"))
        expect(data["total_invocations"]).to(equal(42))
        expect(data["active_agents"]).to(equal(3))


@pytest.mark.asyncio
async def test_get_stats_registry_error(client: AsyncClient, mock_user_headers, mock_db_cursor):
    mock_db_cursor.fetchone.return_value = (10,)

    with patch("api.v1.endpoints.stats.AgentRegistry") as MockRegistry:
        MockRegistry.return_value.get_all.side_effect = Exception("Registry Fail")

        response = await client.get("/stats/", headers=mock_user_headers)
        expect(response.status_code).to(equal(200))
        data = response.json()

        # Should succeed with 0 agents
        expect(data["active_agents"]).to(equal(0))
        expect(data["total_invocations"]).to(equal(10))


@pytest.mark.asyncio
async def test_get_stats_db_error(client: AsyncClient, mock_user_headers):
    # Mock DB failure. Since mock_db_cursor is yielded by db_pool_mock fixture,
    # we can modify it directly, but need to be careful if it's already set up.
    # The fixture mock_db_cursor is a MagicMock for cursor.
    # But stats.py uses `async with pool.connection() as conn: async with conn.cursor() as cur:`
    # The global fixture patches `pool` deeply.

    # We can try to make execute raise exception.
    # But we need to use patch on the module to be sure if fixture is tricky?
    # No, fixture `mock_db_cursor` patches `backend.tests.conftest.mock_db_cursor` which is used by `db_pool_mock`.
    # Let's just use the fixture.

    # Wait, we need to pass `mock_db_cursor` to test to configure it.
    pass


@pytest.mark.asyncio
async def test_get_stats_db_error_implementation(client: AsyncClient, mock_user_headers, mock_db_cursor):
    mock_db_cursor.execute.side_effect = Exception("DB Fail")

    with patch("api.v1.endpoints.stats.AgentRegistry") as MockRegistry:
        MockRegistry.return_value.get_all.return_value = []

        response = await client.get("/stats/", headers=mock_user_headers)
        expect(response.status_code).to(equal(200))
        data = response.json()

        # Should succeed with default 0 invocations
        expect(data["total_invocations"]).to(equal(0))
