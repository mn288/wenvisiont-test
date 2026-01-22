from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.infrastructure import S3Config
from services.infrastructure import InfrastructureService

router = APIRouter()
service = InfrastructureService()


class ConfigRequest(BaseModel):
    s3: Optional[S3Config] = None


class FileItem(BaseModel):
    path: str
    name: str
    type: str


@router.get("/config", response_model=ConfigRequest)
async def get_config():
    """Get current infrastructure config (masked)."""
    # For now, we simulate by reading what the service would load
    # In a real app we'd pass a dummy thread_id or have a separate global config method
    # Hack: We use the direct read from service's persistence logic logic if we extracted it,
    # but for now let's just use get_or_create with a dummy id to see what it picks up
    infra = service.get_or_create_infrastructure("global_settings_check")

    if infra.s3_config:
        # Mask secrets
        masked = infra.s3_config.model_copy()
        if masked.secret_access_key:
            masked.secret_access_key = "********"
        return ConfigRequest(s3=masked)

    return ConfigRequest()


@router.post("/config")
async def update_config(config: ConfigRequest):
    """Update infrastructure config."""
    service.save_config(config.s3)
    return {"status": "updated"}


@router.post("/verify-s3")
async def verify_s3(config: S3Config):
    """Test S3 connection."""
    valid = await service.verify_s3_connection(config)
    if not valid:
        raise HTTPException(status_code=400, detail="Connection failed. Check credentials or permissions.")
    return {"status": "valid"}
