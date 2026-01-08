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
        metadata: dict = None,
    ):
        """
        Log a step event to the database asynchronously.
        content can be a string or a dict (which will be JSON formatted).
        """
        text_content_str = ""
        metadata_json = None

        if isinstance(content, (dict, list)):
            text_content_str = json.dumps(content)
        else:
            text_content_str = str(content)

        if metadata:
            metadata_json = json.dumps(metadata)

        # Use Application Time (UTC) to match LangGraph checkpoints
        from datetime import datetime, timezone

        # Ensure Naive UTC to prevent Postgres from converting to Local Time on insert
        created_at = datetime.now(timezone.utc).replace(tzinfo=None)

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO step_logs (thread_id, step_name, log_type, content, created_at, checkpoint_id, metadata_)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        thread_id,
                        step_name,
                        log_type,
                        text_content_str,
                        created_at,
                        checkpoint_id,
                        metadata_json,
                    ),
                )
                await conn.commit()
