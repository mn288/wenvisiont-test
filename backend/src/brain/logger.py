import json
from typing import Any

from psycopg_pool import AsyncConnectionPool


class LogHandler:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def log_step(
        self,
        thread_id: str,
        step_name: str,
        log_type: str,
        content: Any,
        checkpoint_id: str = None,
    ):
        """
        Log a step event to the database asynchronously.
        content can be a string or a dict (which will be JSON formatted).
        """
        if isinstance(content, (dict, list)):
            content_str = json.dumps(content)
        else:
            content_str = str(content)

        # Use Application Time (UTC) to match LangGraph checkpoints
        from datetime import datetime, timezone

        # Ensure Naive UTC to prevent Postgres from converting to Local Time on insert
        created_at = datetime.now(timezone.utc).replace(tzinfo=None)

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO step_logs (thread_id, step_name, log_type, content, created_at, checkpoint_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        thread_id,
                        step_name,
                        log_type,
                        content_str,
                        created_at,
                        checkpoint_id,
                    ),
                )
                await conn.commit()
