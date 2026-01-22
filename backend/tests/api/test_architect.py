from unittest.mock import AsyncMock, patch

import pytest
from expects import equal, expect
from httpx import AsyncClient

# Model for ArchitectRequest
payload = {"prompt": "Create a superagent for finance"}


@pytest.mark.asyncio
async def test_generate_superagent_success(client: AsyncClient, mock_user_headers):
    # Mock ArchitectService
    with patch("api.v1.endpoints.architect.ArchitectService") as MockService:
        mock_instance = MockService.return_value
        mock_config = {
            "name": "finance_agent",
            "description": "Finance stuff",
            "nodes": [],
            "edges": [],
        }
        mock_instance.generate_graph_config = AsyncMock(return_value=mock_config)

        response = await client.post("/architect/generate", json=payload, headers=mock_user_headers)
        if response.status_code != 200:
            print(f"DEBUG: Response body: {response.json()}")
        expect(response.status_code).to(equal(200))
        data = response.json()
        expect(data["name"]).to(equal("finance_agent"))


@pytest.mark.asyncio
async def test_generate_superagent_value_error(client: AsyncClient, mock_user_headers):
    with patch("api.v1.endpoints.architect.ArchitectService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.generate_graph_config.side_effect = ValueError("Invalid prompt")

        response = await client.post("/architect/generate", json=payload, headers=mock_user_headers)
        expect(response.status_code).to(equal(400))
        expect(response.json()["detail"]).to(equal("Invalid prompt"))


@pytest.mark.asyncio
async def test_generate_superagent_generic_error(client: AsyncClient, mock_user_headers):
    with patch("api.v1.endpoints.architect.ArchitectService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.generate_graph_config.side_effect = Exception("Something went wrong")

        response = await client.post("/architect/generate", json=payload, headers=mock_user_headers)
        expect(response.status_code).to(equal(500))
        expect(response.json()["detail"]).to(equal("Something went wrong"))
