from typing import List

from fastapi import APIRouter, Depends, HTTPException

from api.middleware import get_current_role
from brain.registry import AgentRegistry
from models.architect import GraphConfig

router = APIRouter()


@router.get("/", response_model=List[GraphConfig])
async def list_workflows():
    """List all available workflows (Superagents)."""
    registry = AgentRegistry()
    # Now synchronous because it uses cached workflows loaded at startup/reload
    return registry.get_workflows()


@router.post("/", response_model=GraphConfig)
async def create_or_update_workflow(config: GraphConfig, role: str = Depends(get_current_role)):
    """Save a workflow configuration. Requires EDITOR or ADMIN role."""
    if role not in ["EDITOR", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions. Required: EDITOR or ADMIN")

    try:
        registry = AgentRegistry()
        await registry.save_workflow(config)

        # Reload Graph to pick up new workflow and its agents
        from services.graph_service import GraphService
        await GraphService.get_instance().reload_graph()

        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save workflow: {str(e)}")


@router.delete("/{name}")
async def delete_workflow(name: str, role: str = Depends(get_current_role)):
    """Delete a workflow. Requires ADMIN role."""
    if role != "ADMIN":
        raise HTTPException(status_code=403, detail="Insufficient permissions. Required: ADMIN")

    try:
        registry = AgentRegistry()
        await registry.delete_workflow(name)
        
        # Reload Graph to remove workflow
        from services.graph_service import GraphService
        await GraphService.get_instance().reload_graph()
        
        return {"message": "Workflow deleted"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete workflow: {str(e)}")
