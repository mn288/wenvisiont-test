"""
Cloud Tasks integration for async agent action execution.
Provides 3-5 minute resilience for long-running operations.

Key features:
- Automatic retry with exponential backoff
- OIDC authentication for Cloud Run targets
- Multiple queues for different execution patterns
- Graceful fallback to synchronous execution
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_tasks_client = None


class TaskQueue(str, Enum):
    """Available Cloud Tasks queues."""

    AGENT_ACTIONS = "awp-agent-actions"
    RAG_PROCESSING = "awp-rag-processing"
    HITL_APPROVALS = "awp-hitl-approvals"
    LONG_RUNNING = "awp-long-running"


def _get_settings():
    """Lazy import of settings to avoid circular imports."""
    from core.config import settings

    return settings


def get_tasks_client():
    """
    Lazy initialization of Cloud Tasks client.
    Returns None if Cloud Tasks is not enabled.
    """
    global _tasks_client
    settings = _get_settings()

    if _tasks_client is None and settings.CLOUD_TASKS_ENABLED:
        try:
            from google.cloud import tasks_v2

            _tasks_client = tasks_v2.CloudTasksClient()
            logger.info("Cloud Tasks client initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Cloud Tasks client: {e}")
            _tasks_client = None

    return _tasks_client


async def create_agent_task(
    agent_name: str,
    payload: Dict[str, Any],
    thread_id: str,
    queue: TaskQueue = TaskQueue.AGENT_ACTIONS,
    delay_seconds: int = 0,
    deadline_seconds: int = 300,
) -> Optional[str]:
    """
    Create a Cloud Task for async agent execution.

    This enables resilient execution of agent actions with:
    - Automatic retries on failure
    - Deadline enforcement (default 5 min)
    - OIDC authentication to Cloud Run

    Args:
        agent_name: Name of the agent to execute
        payload: Task payload data (will be JSON serialized)
        thread_id: Session/thread identifier for state tracking
        queue: Target queue (determines retry behavior)
        delay_seconds: Delay before execution starts
        deadline_seconds: Max execution time (default 5 min)

    Returns:
        Task name if created, None for sync fallback
    """
    settings = _get_settings()

    if not settings.CLOUD_TASKS_ENABLED or not settings.GCP_PROJECT_ID:
        logger.debug("Cloud Tasks disabled, returning None for sync execution")
        return None

    client = get_tasks_client()
    if not client:
        return None

    # Build queue path
    parent = client.queue_path(settings.GCP_PROJECT_ID, settings.GCP_REGION, queue.value)

    # Task payload with metadata
    task_payload = {
        "agent_name": agent_name,
        "thread_id": thread_id,
        "payload": payload,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "queue": queue.value,
    }

    # Build the task
    task = {
        "http_request": {
            "http_method": "POST",
            "url": f"{settings.BACKEND_URL}/api/v1/tasks/execute",
            "headers": {
                "Content-Type": "application/json",
                "X-CloudTasks-Queue": queue.value,
            },
            "body": json.dumps(task_payload).encode("utf-8"),
        },
        "dispatch_deadline": {"seconds": deadline_seconds},
    }

    # Add OIDC token for Cloud Run authentication
    if hasattr(settings, "BACKEND_SA_EMAIL") and settings.BACKEND_SA_EMAIL:
        task["http_request"]["oidc_token"] = {
            "service_account_email": settings.BACKEND_SA_EMAIL,
            "audience": settings.BACKEND_URL,
        }

    # Add schedule time if delay requested
    if delay_seconds > 0:
        from google.protobuf import timestamp_pb2

        schedule_time = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        task["schedule_time"] = timestamp_pb2.Timestamp()
        task["schedule_time"].FromDatetime(schedule_time)

    try:
        response = client.create_task(request={"parent": parent, "task": task})
        logger.info(f"Created Cloud Task: {response.name} in queue {queue.value}")
        return response.name

    except Exception as e:
        logger.error(f"Failed to create Cloud Task: {e}")
        return None


async def create_rag_task(
    document_uri: str,
    thread_id: str,
    operation: str = "ingest",
    delay_seconds: int = 0,
) -> Optional[str]:
    """
    Create a Cloud Task for RAG document processing.

    Args:
        document_uri: URI of document to process
        thread_id: Session/thread identifier
        operation: Operation type (ingest, delete, reindex)
        delay_seconds: Delay before processing

    Returns:
        Task name if created
    """
    settings = _get_settings()

    if not settings.CLOUD_TASKS_ENABLED or not settings.GCP_PROJECT_ID:
        return None

    payload = {
        "document_uri": document_uri,
        "operation": operation,
    }

    return await create_agent_task(
        agent_name="rag_processor",
        payload=payload,
        thread_id=thread_id,
        queue=TaskQueue.RAG_PROCESSING,
        delay_seconds=delay_seconds,
        deadline_seconds=600,  # 10 min for document processing
    )


async def create_hitl_approval_task(
    action_id: str,
    thread_id: str,
    user_id: str,
    action_description: str,
    timeout_seconds: int = 86400,  # 24 hours default
) -> Optional[str]:
    """
    Create a Cloud Task for Human-in-the-Loop approval notification.

    Args:
        action_id: Unique ID for the pending action
        thread_id: Session/thread identifier
        user_id: User who needs to approve
        action_description: Human-readable description
        timeout_seconds: Time before auto-rejection

    Returns:
        Task name if created
    """
    settings = _get_settings()

    if not settings.CLOUD_TASKS_ENABLED or not settings.GCP_PROJECT_ID:
        return None

    payload = {
        "action_id": action_id,
        "user_id": user_id,
        "action_description": action_description,
        "timeout_seconds": timeout_seconds,
    }

    return await create_agent_task(
        agent_name="hitl_notifier",
        payload=payload,
        thread_id=thread_id,
        queue=TaskQueue.HITL_APPROVALS,
        delay_seconds=0,
        deadline_seconds=min(timeout_seconds, 300),  # Cap at 5 min dispatch
    )


async def get_task_status(task_name: str) -> Optional[Dict[str, Any]]:
    """
    Get the status of a Cloud Task.

    Args:
        task_name: Full task resource name

    Returns:
        Task status dict or None if not found
    """
    client = get_tasks_client()
    if not client:
        return None

    try:
        task = client.get_task(name=task_name)
        return {
            "name": task.name,
            "create_time": task.create_time.isoformat() if task.create_time else None,
            "schedule_time": task.schedule_time.isoformat() if task.schedule_time else None,
            "dispatch_count": task.dispatch_count,
            "response_count": task.response_count,
            "first_attempt": task.first_attempt.dispatch_time.isoformat() if task.first_attempt else None,
            "last_attempt": task.last_attempt.dispatch_time.isoformat() if task.last_attempt else None,
        }
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        return None
