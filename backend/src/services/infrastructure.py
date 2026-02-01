import os
import shutil
from typing import Dict, List, Optional

import aioboto3
import orjson

from models.infrastructure import InfrastructureConfig, S3Config


def _get_default_workspace() -> str:
    """
    Get default workspace path.
    - In Docker/K8s: WORKSPACE_ROOT env var is set, use that.
    - Locally: Use .data/workspace relative to the backend directory.
    """
    if os.getenv("WORKSPACE_ROOT"):
        return os.getenv("WORKSPACE_ROOT", "/app/data/workspace")

    # Local development: create workspace in backend/.data/workspace
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(backend_dir, ".data", "workspace")


class InfrastructureService:
    # Persist workspace data - this path will be mounted as a Docker volume in prod
    # For local dev, uses backend/.data/workspace
    BASE_WORKSPACE = _get_default_workspace()

    def get_or_create_infrastructure(self, thread_id: str) -> InfrastructureConfig:
        """
        Prepares the infrastructure for a specific thread/session.
        Values are typically fetched from DB or User Settings (Mocks for now).
        """

        # 1. Local Workspace
        # We create a sandboxed folder for this thread within the visible workspace
        # Structure: backend/workspace/{thread_id}/
        workspace_path = os.path.join(self.BASE_WORKSPACE, thread_id)
        if not os.path.exists(workspace_path):
            os.makedirs(workspace_path, exist_ok=True)

        # 2. S3 Config
        # TODO: Fetch from DB based on thread/user context
        # For now, we return None unless specifically set in ENV for testing
        s3_config = None
        if os.getenv("TEST_S3_BUCKET"):
            s3_config = S3Config(
                bucket_name=os.getenv("TEST_S3_BUCKET", ""),
                region_name=os.getenv("TEST_S3_REGION", "us-east-1"),
                access_key_id=os.getenv("TEST_S3_ACCESS_KEY"),
                secret_access_key=os.getenv("TEST_S3_SECRET_KEY"),
            )

        return InfrastructureConfig(local_workspace_path=workspace_path, s3_config=s3_config)

    def cleanup(self, thread_id: str):
        """Clean up tmp assets."""
        path = os.path.join(self.BASE_WORKSPACE, thread_id)
        if os.path.exists(path):
            shutil.rmtree(path)

    def save_config(self, s3_config: Optional[S3Config]):
        """Persist config to disk (Simple JSON implementation)."""
        if not os.path.exists(self.BASE_WORKSPACE):
            os.makedirs(self.BASE_WORKSPACE, exist_ok=True)

        config_path = os.path.join(self.BASE_WORKSPACE, "infra_config.json")
        data = {}
        if s3_config:
            data["s3"] = s3_config.model_dump()

        with open(config_path, "w") as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2).decode())

    def list_files(self, thread_id: str) -> List[Dict[str, str]]:
        """List files in the workspace recursively."""
        workspace = os.path.join(self.BASE_WORKSPACE, thread_id)
        if not os.path.exists(workspace):
            return []

        files_list = []
        for root, _, files in os.walk(workspace):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, workspace)
                files_list.append({"path": rel_path, "name": file, "type": "file"})
        return files_list

    def read_file(self, thread_id: str, file_path: str) -> str:
        """Read a specific file from workspace."""
        workspace = os.path.join(self.BASE_WORKSPACE, thread_id)
        target = os.path.abspath(os.path.join(workspace, file_path))

        if not target.startswith(os.path.abspath(workspace)):
            raise ValueError("Access Denied")

        if not os.path.exists(target):
            raise FileNotFoundError("File not found")

        with open(target, "r") as f:
            return f.read()

    async def verify_s3_connection(self, config: S3Config) -> bool:
        """Check if S3 credentials are valid."""
        session = aioboto3.Session(
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key,
            region_name=config.region_name,
        )
        try:
            async with session.client("s3") as s3:
                # Try listing buckets or specific bucket
                if config.bucket_name:
                    await s3.head_bucket(Bucket=config.bucket_name)
                else:
                    await s3.list_buckets()
            return True
        except Exception:
            return False
