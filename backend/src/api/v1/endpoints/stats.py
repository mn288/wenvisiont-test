from fastapi import APIRouter

from brain.logger import app_logger
from brain.registry import AgentRegistry
from core.database import pool

router = APIRouter()


@router.get("/")
async def get_stats():
    """
    Get Global System Stats.
    """
    stats = {
        "total_invocations": 0,
        "active_agents": 0,
        "compliance_score": 98,  # Placeholder / Hardcoded base
        "system_health": "Healthy",
    }

    # 1. Active Agents
    try:
        registry = AgentRegistry()
        stats["active_agents"] = len(registry.get_all())
    except Exception:
        pass

    # 2. Total Invocations
    # We count unique thread_ids in step_logs as proxy for "Invocations/Jobs"
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT COUNT(DISTINCT thread_id) FROM step_logs")
                row = await cur.fetchone()
                if row:
                    stats["total_invocations"] = row[0]

                # Bonus: We could calculate a "Compliance Score" based on masked PII logs?
                # For now, let's keep it static + small random variance or simple toggle
                # If we find [REDACTED] in logs, we assume compliance is working.

    except Exception as e:
        app_logger.error(f"Stats Error: {e}")

    return stats
