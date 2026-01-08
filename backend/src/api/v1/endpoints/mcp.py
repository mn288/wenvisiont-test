from typing import List

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import require_role
from core.database import pool
from models.mcp import MCPServer, MCPServerCreate

router = APIRouter()


@router.get("/", response_model=List[MCPServer], dependencies=[Depends(require_role("ADMIN"))])
async def list_mcp_servers():
    """List all MCP servers."""
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # We fetch manually to map to Model (or use simple select if using raw SQLModel session - checking consistent pattern in codebase)
                # The codebase seems to use raw asyncpg cursors often with helper text queries?
                # Let's check `stats.py` -> yes, raw SQL.
                # Let's check `registry.py` -> yes, raw SQL.
                # So we stick to raw SQL for consistency.

                await cur.execute("SELECT id, name, type, command, args, url, env FROM mcp_servers ORDER BY name")
                rows = await cur.fetchall()

                servers = []
                for row in rows:
                    servers.append(
                        MCPServer(
                            id=row[0],
                            name=row[1],
                            type=row[2],
                            command=row[3],
                            args=row[4] if row[4] else [],
                            url=row[5],
                            env=row[6] if row[6] else {},
                        )
                    )
                return servers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list MCP servers: {str(e)}")


@router.post("/", response_model=MCPServer, dependencies=[Depends(require_role("ADMIN"))])
async def create_mcp_server(server: MCPServerCreate):
    """Add a new MCP server."""
    # Basic Validation
    if server.type == "stdio" and not server.command:
        raise HTTPException(status_code=400, detail="Command is required for stdio type")
    if server.type in ["sse", "https"] and not server.url:
        raise HTTPException(status_code=400, detail="URL is required for sse/https type")

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # Check duplication
                await cur.execute("SELECT 1 FROM mcp_servers WHERE name = %s", (server.name,))
                if await cur.fetchone():
                    raise HTTPException(status_code=409, detail=f"MCP Server '{server.name}' already exists")

                import json

                await cur.execute(
                    """
                    INSERT INTO mcp_servers (name, type, command, args, url, env, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    RETURNING id
                    """,
                    (
                        server.name,
                        server.type,
                        server.command,
                        server.args,
                        server.url,
                        json.dumps(server.env) if server.env else None,
                    ),
                )
                new_id = await cur.fetchone()
                await conn.commit()

                # Return created object
                return MCPServer(
                    id=new_id[0],
                    name=server.name,
                    type=server.type,
                    command=server.command,
                    args=server.args,
                    url=server.url,
                    env=server.env,
                )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create MCP server: {str(e)}")


@router.delete("/{name}", dependencies=[Depends(require_role("ADMIN"))])
async def delete_mcp_server(name: str):
    """Delete an MCP server."""
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                result = await cur.execute("DELETE FROM mcp_servers WHERE name = %s", (name,))
                if result.rowcount == 0:
                    raise HTTPException(status_code=404, detail="MCP Server not found")
                await conn.commit()
                return {"message": f"MCP Server {name} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete MCP server: {str(e)}")
