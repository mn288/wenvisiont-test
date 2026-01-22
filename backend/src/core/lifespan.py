from contextlib import asynccontextmanager

from fastapi import FastAPI

from brain.registry import AgentRegistry
from core.database import pool
from services.graph_service import GraphService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Open DB pool
    await pool.open()

    # Load Agents from DB
    await AgentRegistry().load_agents()

    # Initial Graph Load
    await GraphService.get_instance().reload_graph()
    
    # Verify Langfuse Connection
    try:
        from core.observability import get_langfuse_client
        client = get_langfuse_client()
        if client:
            print("Langfuse Client Initialized successfully. Sending test trace...")
            # Send a test trace to verify PROOF OF CONNECTION
            # v3: use start_span (creates a root span/trace)
            span = client.start_span(name="Startup Test Trace", metadata={"user_id": "admin"})
            span.end()
            client.flush()
            print("Test trace flushed. Check dashboard for 'Startup Test Trace'.")
    except Exception as e:
        print(f"WARNING: Langfuse initialization failed: {e}")

    yield

    # Shutdown: Close DB pool
    await pool.close()
    
    # Check for pending traces
    from core.observability import shutdown_langfuse
    shutdown_langfuse()
