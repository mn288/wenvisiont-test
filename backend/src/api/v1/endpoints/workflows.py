import glob
import os
from typing import List

import yaml
from fastapi import APIRouter, Depends, HTTPException

from api.middleware import get_current_role
from models.architect import GraphConfig

router = APIRouter()

WORKFLOWS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "config", "workflows"
)

# Ensure directory exists
os.makedirs(WORKFLOWS_DIR, exist_ok=True)


@router.get("/", response_model=List[GraphConfig])
async def list_workflows():
    """List all available workflows (Superagents)."""
    configs = []
    yaml_files = glob.glob(os.path.join(WORKFLOWS_DIR, "*.yaml"))

    for file_path in yaml_files:
        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
                configs.append(GraphConfig(**data))
        except Exception as e:
            print(f"Error loading workflow {file_path}: {e}")

    return configs


@router.post("/", response_model=GraphConfig)
async def create_or_update_workflow(config: GraphConfig, role: str = Depends(get_current_role)):
    """Save a workflow configuration. Requires EDITOR or ADMIN role."""
    if role not in ["EDITOR", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions. Required: EDITOR or ADMIN")

    file_path = os.path.join(WORKFLOWS_DIR, f"{config.name}.yaml")

    try:
        # Convert to dict
        data = config.model_dump(exclude_none=True)

        with open(file_path, "w") as f:
            yaml.dump(data, f, sort_keys=False, default_flow_style=False)

        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save workflow: {str(e)}")


@router.delete("/{name}")
async def delete_workflow(name: str, role: str = Depends(get_current_role)):
    """Delete a workflow. Requires ADMIN role."""
    if role != "ADMIN":
        raise HTTPException(status_code=403, detail="Insufficient permissions. Required: ADMIN")

    file_path = os.path.join(WORKFLOWS_DIR, f"{name}.yaml")

    if os.path.exists(file_path):
        os.remove(file_path)
        return {"message": "Workflow deleted"}

    raise HTTPException(status_code=404, detail="Workflow not found")
