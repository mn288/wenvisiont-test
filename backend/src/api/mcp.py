import json
from typing import List

from fastapi import APIRouter, HTTPException

from core.database import pool
from models.mcp import MCPServerConfig, MCPServerCreate

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/servers", response_model=List[MCPServerConfig])
async def list_servers():
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, name, type, command, args, url, env FROM mcp_servers ORDER BY created_at DESC"
            )
            rows = await cur.fetchall()
            return [
                MCPServerConfig(
                    id=row[0],
                    name=row[1],
                    type=row[2],
                    command=row[3],
                    args=row[4] if row[4] else [],
                    url=row[5],
                    env=row[6] if row[6] else {},
                )
                for row in rows
            ]


@router.post("/servers", response_model=MCPServerConfig)
async def add_server(server: MCPServerCreate):
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            try:
                await cur.execute(
                    """
                    INSERT INTO mcp_servers (name, type, command, args, url, env)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        server.name,
                        server.type,
                        server.command,
                        server.args,
                        server.url,
                        json.dumps(server.env) if server.env else "{}",
                    ),
                )
                new_id = await cur.fetchone()
                # await conn.commit() # Not needed with autocommit or context manager if pool handles it?
                # Pool usage with 'async with pool.connection() as conn' usually requires explicit commit unless autocommit is on.
                # In standard psycopg 3 with pool, we should commit.
                await conn.commit()

                return MCPServerConfig(id=new_id[0], **server.dict())
            except Exception as e:
                await conn.rollback()
                raise HTTPException(status_code=400, detail=str(e))


@router.delete("/servers/{server_id}")
async def delete_server(server_id: int):
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM mcp_servers WHERE id = %s", (server_id,))
            await conn.commit()
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Server not found")
    return {"status": "success"}
