import logging
import sys
from datetime import datetime, timezone
from typing import Any

import orjson


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Merge extra attributes (structured data)
        if hasattr(record, "structured_data"):
            log_obj.update(record.structured_data)

        return orjson.dumps(log_obj).decode("utf-8")


def setup_logger(name: str = "antigravity") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Controlled by env in real app, defaulting to DEBUG for now

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    return logger


# Global Logger Instance
app_logger = setup_logger()


class LogHandler:
    """
    Legacy Adapter: Maintains the signature of the old Postgres LogHandler
    but writes to Stdout using the new Structured Logger.
    """

    def __init__(self, pool: Any = None):
        # Pool is no longer used, but kept for signature compatibility during transition
        pass

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
        Log a step event to Stdout (JSON).
        This is an Async method to match the interface, but logging is sync (fast).
        """

        # Prepare structured data
        structured_data = {
            "thread_id": thread_id,
            "step_name": step_name,
            "log_type": log_type,
            "checkpoint_id": checkpoint_id,
        }

        if metadata:
            structured_data["metadata"] = metadata

        # Parse content
        msg = ""
        if isinstance(content, (dict, list)):
            try:
                msg = orjson.dumps(content).decode()
                # If content is a dict, we might want to merge it?
                # For now, keep it as the "message" or a separate field "content_json"
                # to keep the "message" cleanly readable.
                structured_data["content_json"] = content
                msg = "Structured Content Logged"
            except Exception:
                msg = str(content)
        else:
            msg = str(content)

        # Map log_type to Level
        level = logging.INFO
        if log_type.lower() in ["error", "critical"]:
            level = logging.ERROR
        elif log_type.lower() in ["warning", "warn"]:
            level = logging.WARNING
        elif log_type.lower() in ["debug", "thought"]:
            level = logging.DEBUG

        # Create a LogRecord manually or use the adapter approach
        # Using extra=... with the standard logger is cleaner
        app_logger.log(level, msg, extra={"structured_data": structured_data})
