from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from api.dependencies import get_session, require_role
from brain.logger import app_logger
from brain.registry import AgentRegistry
from models.mcp import MCPServer, MCPServerCreate
from services.graph_service import GraphService
from services.mcp import mcp_service

router = APIRouter()


async def background_system_reload(server_name: str, action: str):
    """
    Background task to reload the system (Agents + Graph) after a change.
    """
    try:
        app_logger.info(f"Background Task: Reloading system after {action} of MCP Server '{server_name}'...")
        await AgentRegistry().load_agents()
        await GraphService.get_instance().reload_graph()
        app_logger.info("Background Task: System reload complete.")
    except Exception as e:
        app_logger.error(f"Background Task Error: Failed to reload system: {e}")


@router.get("/", response_model=List[MCPServer], dependencies=[Depends(require_role("ADMIN"))])
async def list_mcp_servers(session: AsyncSession = Depends(get_session)):
    """List all MCP servers."""
    try:
        return await mcp_service.get_all_servers(session=session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list MCP servers: {str(e)}")


@router.post("/", response_model=MCPServer, dependencies=[Depends(require_role("ADMIN"))])
async def create_mcp_server(
    server: MCPServerCreate, background_tasks: BackgroundTasks, session: AsyncSession = Depends(get_session)
):
    """Add a new MCP server. Reloads system in background."""
    # Basic Validation
    if server.type == "stdio" and not server.command:
        raise HTTPException(status_code=400, detail="Command is required for stdio type")
    if server.type in ["sse", "https"] and not server.url:
        raise HTTPException(status_code=400, detail="URL is required for sse/https type")

    try:
        new_server = await mcp_service.create_server(server, session=session)

        # Trigger Reload in Background
        background_tasks.add_task(background_system_reload, new_server.name, "creation")

        return new_server
    except ValueError as e:
        # Check for duplication (handled in service now, but message matching helps)
        if "already exists" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=f"Connection Failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create MCP server: {str(e)}")


@router.delete("/{name}", dependencies=[Depends(require_role("ADMIN"))])
async def delete_mcp_server(name: str, background_tasks: BackgroundTasks, session: AsyncSession = Depends(get_session)):
    """Delete an MCP server. Reloads system in background."""
    try:
        deleted = await mcp_service.delete_server(name, session=session)
        if not deleted:
            raise HTTPException(status_code=404, detail="MCP Server not found")

        # Trigger Reload in Background
        background_tasks.add_task(background_system_reload, name, "deletion")

        return {"message": f"MCP Server {name} deleted. System reload scheduled."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete MCP server: {str(e)}")


@router.post("/reload", dependencies=[Depends(require_role("ADMIN"))])
async def reload_system(background_tasks: BackgroundTasks):
    """Manually trigger a system reload (Background Task)."""
    try:
        background_tasks.add_task(background_system_reload, "Manual", "request")
        return {"status": "accepted", "message": "System reload scheduled in background."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reload failed: {str(e)}")
