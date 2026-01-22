import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.infrastructure import InfrastructureService

router = APIRouter()

# Allow listing files in the project root (or specific safe directories)
# For this demo, we'll assume the workspace root is safe, but we should traverse up carefully.
# In a real app, restrict this to a sandbox.
# Point to a dedicated workspace folder for agent outputs
WORKSPACE_ROOT = InfrastructureService.BASE_WORKSPACE
if not os.path.exists(WORKSPACE_ROOT):
    os.makedirs(WORKSPACE_ROOT, exist_ok=True)


class FileItem(BaseModel):
    name: str
    path: str
    type: str  # 'file' or 'directory'
    size: Optional[int] = 0


class ReadFileRequest(BaseModel):
    path: str


@router.get("/list", response_model=List[FileItem])
async def list_files(path: str = "."):
    """List files in the specified directory (relative to workspace root)."""

    # Security check: Prevent traversing up too far
    if ".." in path:
        raise HTTPException(status_code=400, detail="Invalid path")

    full_path = os.path.join(WORKSPACE_ROOT, path)

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Path not found")

    items = []
    try:
        with os.scandir(full_path) as it:
            for entry in it:
                items.append(
                    FileItem(
                        name=entry.name,
                        path=os.path.join(path, entry.name),
                        type="directory" if entry.is_dir() else "file",
                        size=entry.stat().st_size if entry.is_file() else 0,
                    )
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Sort: Directories first, then files
    items.sort(key=lambda x: (x.type != "directory", x.name))
    return items


@router.post("/read")
async def read_file(request: ReadFileRequest):
    """Read content of a file."""

    # Security check
    if ".." in request.path:
        raise HTTPException(status_code=400, detail="Invalid path")

    full_path = os.path.join(WORKSPACE_ROOT, request.path)

    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
            return {"content": content, "path": request.path}
    except UnicodeDecodeError:
        return {"content": "[Binary File]", "path": request.path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
