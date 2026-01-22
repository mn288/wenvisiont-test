from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.database import pool

router = APIRouter()


class ConfigItem(BaseModel):
    key: str
    value: Dict[str, Any]


@router.get("/{key}", response_model=ConfigItem)
async def get_config(key: str):
    """Get configuration by key."""
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT key, value FROM configurations WHERE key = %s", (key,))
            row = await cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Configuration not found")
            return ConfigItem(key=row[0], value=row[1])


@router.post("/", response_model=ConfigItem)
async def create_or_update_config(config: ConfigItem):
    """Create or update configuration."""
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO configurations (key, value, updated_at) 
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (key) 
                DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
                """,
                (config.key, config.value),
            )
            return config


@router.delete("/{key}")
async def delete_config(key: str):
    """Delete configuration by key."""
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM configurations WHERE key = %s", (key,))
            return {"status": "success", "message": f"Configuration {key} deleted"}
