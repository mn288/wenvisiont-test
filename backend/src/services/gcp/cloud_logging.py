"""
Cloud Logging integration for structured observability.
Exports traces and logs from Langfuse to Cloud Logging for
unified monitoring in GCP.

Key features:
- Structured JSON logging
- Correlation with Cloud Trace
- Integration with Cloud Monitoring
- Log-based metrics for alerting
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_cloud_logging_configured = False


def _get_settings():
    """Lazy import of settings to avoid circular imports."""
    from core.config import settings

    return settings


def setup_cloud_logging() -> bool:
    """
    Configure Cloud Logging for the application.

    This sets up structured logging to Cloud Logging, enabling:
    - Centralized log aggregation
    - Log-based alerting
    - Integration with Cloud Trace

    Returns:
        True if successfully configured
    """
    global _cloud_logging_configured
    settings = _get_settings()

    if not settings.CLOUD_LOGGING_ENABLED or not settings.GCP_PROJECT_ID:
        logger.debug("Cloud Logging not enabled")
        return False

    if _cloud_logging_configured:
        return True

    try:
        import google.cloud.logging
        # Create client
        client = google.cloud.logging.Client(project=settings.GCP_PROJECT_ID)

        # Setup structured logging
        client.setup_logging()

        _cloud_logging_configured = True
        logger.info(f"Cloud Logging configured for project {settings.GCP_PROJECT_ID}")
        return True

    except ImportError:
        logger.warning("google-cloud-logging not installed")
        return False
    except Exception as e:
        logger.error(f"Failed to configure Cloud Logging: {e}")
        return False


def log_structured(
    message: str,
    severity: str = "INFO",
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    labels: Optional[Dict[str, str]] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Write a structured log entry to Cloud Logging.

    This enables correlation with Cloud Trace and rich metadata
    for log analysis.

    Args:
        message: Log message
        severity: Log severity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        trace_id: Cloud Trace ID for correlation
        span_id: Span ID within the trace
        labels: Custom labels for filtering
        payload: Additional structured data
    """
    settings = _get_settings()

    # Build structured log entry
    log_entry = {
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "severity": severity.upper(),
        "labels": labels or {},
    }

    # Add trace context for Cloud Trace correlation
    if trace_id:
        log_entry["logging.googleapis.com/trace"] = f"projects/{settings.GCP_PROJECT_ID}/traces/{trace_id}"

    if span_id:
        log_entry["logging.googleapis.com/spanId"] = span_id

    # Add payload
    if payload:
        log_entry["jsonPayload"] = payload

    # Log using appropriate level
    log_level = getattr(logging, severity.upper(), logging.INFO)

    if settings.CLOUD_LOGGING_ENABLED and _cloud_logging_configured:
        # Use struct for Cloud Logging
        logger.log(log_level, json.dumps(log_entry))
    else:
        # Standard logging
        logger.log(log_level, message, extra=payload or {})


def log_agent_execution(
    agent_name: str,
    thread_id: str,
    status: str,
    duration_ms: int,
    trace_id: Optional[str] = None,
    error: Optional[str] = None,
    output_summary: Optional[str] = None,
) -> None:
    """
    Log agent execution with structured metadata.

    Creates a log entry optimized for agent monitoring and debugging.

    Args:
        agent_name: Name of the executed agent
        thread_id: Session/thread identifier
        status: Execution status (success, failure, timeout)
        duration_ms: Execution duration in milliseconds
        trace_id: Trace ID for correlation
        error: Error message if failed
        output_summary: Summary of agent output
    """
    payload = {
        "agent_name": agent_name,
        "thread_id": thread_id,
        "status": status,
        "duration_ms": duration_ms,
    }

    if error:
        payload["error"] = error

    if output_summary:
        payload["output_summary"] = output_summary[:500]  # Truncate

    severity = "ERROR" if status == "failure" else "INFO"

    log_structured(
        message=f"Agent {agent_name} {status} in {duration_ms}ms",
        severity=severity,
        trace_id=trace_id,
        labels={
            "agent_name": agent_name,
            "status": status,
        },
        payload=payload,
    )


def log_rag_query(
    query: str,
    source: str,
    result_count: int,
    duration_ms: int,
    trace_id: Optional[str] = None,
    avg_score: Optional[float] = None,
) -> None:
    """
    Log RAG query execution for monitoring retrieval quality.

    Args:
        query: Search query (truncated for privacy)
        source: RAG source (corpus, discovery_engine)
        result_count: Number of results returned
        duration_ms: Query duration
        trace_id: Trace ID for correlation
        avg_score: Average relevance score
    """
    payload = {
        "query_preview": query[:100] if query else "",  # Truncate for privacy
        "source": source,
        "result_count": result_count,
        "duration_ms": duration_ms,
    }

    if avg_score is not None:
        payload["avg_score"] = round(avg_score, 3)

    log_structured(
        message=f"RAG query to {source}: {result_count} results in {duration_ms}ms",
        severity="INFO",
        trace_id=trace_id,
        labels={
            "source": source,
            "has_results": str(result_count > 0).lower(),
        },
        payload=payload,
    )


def log_llm_call(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration_ms: int,
    trace_id: Optional[str] = None,
    cache_hit: bool = False,
) -> None:
    """
    Log LLM API call for cost and performance monitoring.

    Args:
        model: Model name
        prompt_tokens: Input token count
        completion_tokens: Output token count
        duration_ms: Call duration
        trace_id: Trace ID for correlation
        cache_hit: Whether response was cached
    """
    total_tokens = prompt_tokens + completion_tokens

    payload = {
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "duration_ms": duration_ms,
        "cache_hit": cache_hit,
    }

    log_structured(
        message=f"LLM call to {model}: {total_tokens} tokens in {duration_ms}ms",
        severity="INFO",
        trace_id=trace_id,
        labels={
            "model": model,
            "cache_hit": str(cache_hit).lower(),
        },
        payload=payload,
    )


def log_security_event(
    event_type: str,
    user_id: Optional[str],
    resource: str,
    action: str,
    allowed: bool,
    trace_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log security-related events for audit trail.

    Args:
        event_type: Type of security event (auth, access, pii_detected)
        user_id: User performing the action
        resource: Resource being accessed
        action: Action being performed
        allowed: Whether action was allowed
        trace_id: Trace ID for correlation
        details: Additional event details
    """
    payload = {
        "event_type": event_type,
        "user_id": user_id or "anonymous",
        "resource": resource,
        "action": action,
        "allowed": allowed,
    }

    if details:
        payload["details"] = details

    severity = "WARNING" if not allowed else "INFO"

    log_structured(
        message=f"Security: {event_type} - {action} on {resource} {'allowed' if allowed else 'denied'}",
        severity=severity,
        trace_id=trace_id,
        labels={
            "event_type": event_type,
            "allowed": str(allowed).lower(),
        },
        payload=payload,
    )
