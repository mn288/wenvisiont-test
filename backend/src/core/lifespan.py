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

    yield

    # Shutdown: Close DB pool
    await pool.close()
