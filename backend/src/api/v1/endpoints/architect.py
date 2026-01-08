from fastapi import APIRouter, Depends, HTTPException

from api.middleware import get_current_tenant_id
from models.architect import ArchitectRequest, GraphConfig
from services.architect_service import ArchitectService

router = APIRouter()


@router.post("/generate", response_model=GraphConfig)
async def generate_superagent(
    request: ArchitectRequest,
    tenant_id: str = Depends(get_current_tenant_id),  # Enforce tenant context
):
    """
    Generate a new Superagent configuration from a natural language prompt.
    Required X-Tenant-ID header.
    """
    service = ArchitectService()
    try:
        config = await service.generate_graph_config(request.prompt)
        return config
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
