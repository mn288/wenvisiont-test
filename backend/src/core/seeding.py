import orjson

from brain.logger import app_logger
from core.database import pool


async def seed_infrastructure():
    """
    Seeds the infrastructure configuration if it doesn't exist.
    This ensures that on fresh installs, the system has the necessary defaults.
    """
    # Default configuration matching the environment
    # Note: local_workspace_path must match the container's volume mount
    default_config = {"local_workspace_path": "/app/data/workspace", "allowed_mcp_servers": [], "s3_access": {}}

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # Check if config exists
                await cur.execute("SELECT 1 FROM configurations WHERE key = 'infrastructure_config'")
                row = await cur.fetchone()

                if not row:
                    app_logger.info("SEEDER: infrastructure_config not found. Seeding defaults...")
                    await cur.execute(
                        """
                        INSERT INTO configurations (key, value, updated_at) 
                        VALUES (%s, %s, CURRENT_TIMESTAMP)
                        """,
                        ("infrastructure_config", orjson.dumps(default_config).decode()),
                    )
                    app_logger.info("SEEDER: infrastructure_config seeded successfully.")
                else:
                    app_logger.info("SEEDER: infrastructure_config already exists.")

    except Exception as e:
        app_logger.error(f"SEEDER: Failed to seed infrastructure config: {e}")
