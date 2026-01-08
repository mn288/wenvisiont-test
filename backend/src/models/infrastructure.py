from typing import List, Optional

from pydantic import BaseModel, Field


class S3Config(BaseModel):
    """Configuration for S3 Access."""

    bucket_name: str
    region_name: str = "us-east-1"
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    endpoint_url: Optional[str] = None


class InfrastructureConfig(BaseModel):
    """
    Runtime configuration for Agent Infrastructure.
    Defines where the agent is allowed to read/write files.
    """

    local_workspace_path: str = Field(..., description="Absolute path to the local workspace root.")
    s3_config: Optional[S3Config] = Field(None, description="S3 Credentials if enabled.")


class TenantConfig(BaseModel):
    """
    Tenant-level configuration stored in the 'configurations' table.
    Used to control access to infrastructure resources.
    """

    local_workspace_path: Optional[str] = Field(None, description="Absolute path to the local workspace root.")
    s3_config: Optional[S3Config] = Field(None, description="S3 Credentials if enabled.")
    allowed_mcp_servers: List[str] = Field(
        default_factory=list, description="List of MCP server names this tenant can use."
    )
