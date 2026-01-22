import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.s3 import AsyncS3ReadTool, AsyncS3WriteTool, S3Config


@pytest.mark.asyncio
async def test_s3_read_tool_mocked():
    """
    Verifies that AsyncS3ReadTool calls generate_presigned_url ('get_object')
    and then fetches content via aiohttp.
    """
    mock_s3_config = S3Config(bucket_name="test-bucket", access_key_id="test-key", secret_access_key="test-secret")

    with (
        patch("tools.s3.aioboto3.Session") as MockSession,
        patch("tools.s3.aiohttp.ClientSession") as MockClientSession,
    ):
        # Mock S3 Client and generate_presigned_url
        mock_s3_client = AsyncMock()
        mock_s3_client.generate_presigned_url.return_value = "http://presigned-url.com/obj"

        # Mock Session Context Manager
        mock_session_instance = MagicMock()
        mock_session_instance.client.return_value.__aenter__.return_value = mock_s3_client
        MockSession.return_value = mock_session_instance

        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read.return_value = b"file content"

        # Mock http session get (returns a context manager, NOT a coroutine)
        mock_http_session = MagicMock()
        mock_get_ctx = MagicMock()
        mock_get_ctx.__aenter__.return_value = mock_response
        mock_get_ctx.__aexit__.return_value = None
        mock_http_session.get.return_value = mock_get_ctx

        MockClientSession.return_value.__aenter__.return_value = mock_http_session

        # Run Tool
        tool = AsyncS3ReadTool(s3_config=mock_s3_config)
        result = await tool._arun(bucket="test-bucket", key="test-key")

        # Assertions
        assert result == "file content"
        mock_s3_client.generate_presigned_url.assert_called_with(
            ClientMethod="get_object", Params={"Bucket": "test-bucket", "Key": "test-key"}, ExpiresIn=3600
        )
        mock_http_session.get.assert_called_with("http://presigned-url.com/obj")
        print("AsyncS3ReadTool verification passed!")


@pytest.mark.asyncio
async def test_s3_write_tool_mocked():
    """
    Verifies that AsyncS3WriteTool calls generate_presigned_url ('put_object')
    and then uploads content via aiohttp.
    """
    mock_s3_config = S3Config(bucket_name="test-bucket", access_key_id="test-key", secret_access_key="test-secret")

    with (
        patch("tools.s3.aioboto3.Session") as MockSession,
        patch("tools.s3.aiohttp.ClientSession") as MockClientSession,
    ):
        # Mock S3 Client and generate_presigned_url
        mock_s3_client = AsyncMock()
        mock_s3_client.generate_presigned_url.return_value = "http://presigned-url.com/obj"

        # Mock Session Context Manager
        mock_session_instance = MagicMock()
        mock_session_instance.client.return_value.__aenter__.return_value = mock_s3_client
        MockSession.return_value = mock_session_instance

        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.status = 200

        # Mock http session put (returns a context manager)
        mock_http_session = MagicMock()
        mock_put_ctx = MagicMock()
        mock_put_ctx.__aenter__.return_value = mock_response
        mock_put_ctx.__aexit__.return_value = None
        mock_http_session.put.return_value = mock_put_ctx

        MockClientSession.return_value.__aenter__.return_value = mock_http_session

        # Run Tool
        tool = AsyncS3WriteTool(s3_config=mock_s3_config)
        result = await tool._arun(bucket="test-bucket", key="test-key", content="new content")

        # Assertions
        assert "Successfully uploaded" in result
        mock_s3_client.generate_presigned_url.assert_called_with(
            ClientMethod="put_object", Params={"Bucket": "test-bucket", "Key": "test-key"}, ExpiresIn=3600
        )
        # Ensure aiohttp put was called with correct URL and data
        mock_http_session.put.assert_called_with("http://presigned-url.com/obj", data=b"new content")
        print("AsyncS3WriteTool verification passed!")


if __name__ == "__main__":
    # Manually running async tests for quick check if not using pytest runner directly
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_s3_read_tool_mocked())
    loop.run_until_complete(test_s3_write_tool_mocked())
    loop.close()
