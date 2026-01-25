import nest_asyncio
from fastapi import FastAPI

from api.v1.endpoints.agents import router as agents_router
from api.v1.endpoints.architect import router as architect_router
from api.v1.endpoints.config_endpoints import router as config_router
from api.v1.endpoints.execution import router as execution_router
from api.v1.endpoints.files import router as files_router
from api.v1.endpoints.history import router as history_router
from api.v1.endpoints.infrastructure import router as infra_router
from api.v1.endpoints.mcp import router as mcp_router
from api.v1.endpoints.stats import router as stats_router
from api.v1.endpoints.workflows import router as workflow_router
from core.lifespan import lifespan
from core.middleware import configure_middleware

# Allow nested event loops for CrewAI sync tool wrappers
nest_asyncio.apply()

app = FastAPI(title="LangGraph-CrewAI Bridge", lifespan=lifespan)

configure_middleware(app)

app.include_router(mcp_router, prefix="/mcp", tags=["mcp"])
app.include_router(agents_router, prefix="/agents", tags=["agents"])
app.include_router(config_router, prefix="/configurations", tags=["configurations"])
app.include_router(architect_router, prefix="/architect", tags=["architect"])
app.include_router(workflow_router, prefix="/workflows", tags=["workflows"])
app.include_router(infra_router, prefix="/infrastructure", tags=["infrastructure"])
app.include_router(files_router, prefix="/files", tags=["files"])
app.include_router(execution_router, tags=["execution"])  # Root level as used directly
app.include_router(history_router, prefix="/history", tags=["history"])
app.include_router(stats_router, prefix="/stats", tags=["stats"])


@app.get("/health")
async def health():
    return {"status": "ok"}
