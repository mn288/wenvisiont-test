import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from brain.registry import AgentRegistry
from core.database import pool
from services.graph_service import GraphService


def run_migrations():
    """Run Alembic migrations programmatically (synchronous)."""
    import os

    from alembic.config import Config

    from alembic import command
    
    # Use absolute path in Docker container
    alembic_ini_path = "/app/backend/alembic.ini"
    alembic_scripts_path = "/app/backend/alembic"
    
    # Fallback for local development
    if not os.path.exists(alembic_ini_path):
        base_path = os.path.join(os.path.dirname(__file__), "..", "..")
        alembic_ini_path = os.path.join(base_path, "alembic.ini")
        alembic_scripts_path = os.path.join(base_path, "alembic")
    
    alembic_cfg = Config(alembic_ini_path)
    alembic_cfg.set_main_option("script_location", alembic_scripts_path)
    
    # Run migrations
    command.upgrade(alembic_cfg, "head")
    print("Alembic migrations applied successfully.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Open DB pool
    await pool.open()

    # Run Alembic Migrations (in thread pool since it's sync)
    try:
        await asyncio.get_event_loop().run_in_executor(None, run_migrations)
    except Exception as e:
        print(f"WARNING: Migration failed (tables may already exist): {e}")

    # Seed Infrastructure Config 
    from core.seeding import seed_infrastructure
    await seed_infrastructure()

    # Seed Default MCP Servers (Filesystem, etc.)
    from brain.seeder import seed_agents, seed_mcp_servers
    await seed_mcp_servers()

    # Seed Agents from Config (Dynamic Loading)
    await seed_agents()

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
