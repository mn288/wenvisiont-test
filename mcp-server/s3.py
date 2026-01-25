import os
import aioboto3
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP


# Initialize FastMCP Server
mcp = FastMCP("s3", dependencies=["aioboto3"], host="0.0.0.0")
mcp_app = mcp.sse_app()
app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "ok"}


app.mount("/", mcp_app)


def _get_session():
    return aioboto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )


@mcp.tool()
async def list_buckets() -> str:
    """Lists all S3 buckets available to the current credentials."""
    session = _get_session()
    try:
        async with session.client("s3") as s3:
            response = await s3.list_buckets()
            buckets = [b["Name"] for b in response.get("Buckets", [])]
            return "\\n".join(buckets)
    except Exception as e:
        return f"Error listing buckets: {str(e)}"


@mcp.tool()
async def read_object(bucket: str, key: str) -> str:
    """Reads the content of an object from S3."""
    session = _get_session()
    try:
        async with session.client("s3") as s3:
            # For simplicity in MCP, we read directly if size allows, otherwise presigned URL might be better for clients?
            # Existing tool logic used presigned URL then http get.
            # Ideally the MCP tool returns text content directly for the LLM.

            # Using direct get_object for text content
            response = await s3.get_object(Bucket=bucket, Key=key)
            async with response["Body"] as stream:
                content = await stream.read()
                return content.decode("utf-8")
    except Exception as e:
        return f"Error reading S3 object: {str(e)}"


@mcp.tool()
async def write_object(bucket: str, key: str, content: str) -> str:
    """Writes content to an S3 object."""
    session = _get_session()
    try:
        async with session.client("s3") as s3:
            await s3.put_object(Bucket=bucket, Key=key, Body=content.encode("utf-8"))
        return f"Successfully uploaded to s3://{bucket}/{key}"
    except Exception as e:
        return f"Error writing S3 object: {str(e)}"


@mcp.tool()
async def delete_object(bucket: str, key: str) -> str:
    """Deletes an S3 object."""
    session = _get_session()
    try:
        async with session.client("s3") as s3:
            await s3.delete_object(Bucket=bucket, Key=key)
        return f"Successfully deleted s3://{bucket}/{key}"
    except Exception as e:
        return f"Error deleting S3 object: {str(e)}"


if __name__ == "__main__":
    mcp.run()
