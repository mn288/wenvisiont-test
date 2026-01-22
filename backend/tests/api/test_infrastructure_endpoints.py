from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from expects import equal, expect
from httpx import AsyncClient

from models.infrastructure import S3Config


@pytest.fixture
def mock_service():
    with patch("api.v1.endpoints.infrastructure.service") as mock_srv:
        yield mock_srv


@pytest.mark.asyncio
async def test_get_config(client: AsyncClient, mock_service):
    # Mock return value of get_or_create_infrastructure
    mock_infra = MagicMock()
    mock_infra.s3_config = S3Config(
        bucket_name="test-bucket", region="us-east-1", access_key_id="key", secret_access_key="secret"
    )
    mock_service.get_or_create_infrastructure.return_value = mock_infra

    response = await client.get("/infrastructure/config")
    expect(response.status_code).to(equal(200))
    data = response.json()
    expect(data["s3"]["secret_access_key"]).to(equal("********"))


@pytest.mark.asyncio
async def test_get_config_empty(client: AsyncClient, mock_service):
    mock_infra = MagicMock()
    mock_infra.s3_config = None
    mock_service.get_or_create_infrastructure.return_value = mock_infra

    response = await client.get("/infrastructure/config")
    expect(response.status_code).to(equal(200))
    expect(response.json()["s3"]).to(equal(None))


@pytest.mark.asyncio
async def test_update_config(client: AsyncClient, mock_service):
    payload = {
        "s3": {
            "bucket_name": "new-bucket",
            "region": "us-west-1",
            "access_key_id": "new",
            "secret_access_key": "new_secret",
        }
    }
    response = await client.post("/infrastructure/config", json=payload)
    expect(response.status_code).to(equal(200))
    expect(mock_service.save_config.called).to(equal(True))


@pytest.mark.asyncio
async def test_verify_s3_success(client: AsyncClient, mock_service):
    mock_service.verify_s3_connection = AsyncMock(return_value=True)
    payload = {"bucket_name": "b", "region": "r", "access_key_id": "k", "secret_access_key": "s"}
    response = await client.post("/infrastructure/verify-s3", json=payload)
    expect(response.status_code).to(equal(200))
    expect(response.json()["status"]).to(equal("valid"))


@pytest.mark.asyncio
async def test_verify_s3_failure(client: AsyncClient, mock_service):
    mock_service.verify_s3_connection = AsyncMock(return_value=False)
    payload = {"bucket_name": "b", "region": "r", "access_key_id": "k", "secret_access_key": "s"}
    response = await client.post("/infrastructure/verify-s3", json=payload)
    expect(response.status_code).to(equal(400))
