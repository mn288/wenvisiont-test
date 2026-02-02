from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from psycopg import AsyncConnection

from brain.graph import build_workflow
from brain.logger import app_logger
from core.config import settings
from core.database import pool


class GraphService:
    _instance = None
    _tables_initialized = False

    def __init__(self):
        self.compiled_graph: CompiledStateGraph = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = GraphService()
        return cls._instance

    async def get_graph(self) -> CompiledStateGraph:
        """Returns the current compiled graph, initializing it if necessary."""
        if self.compiled_graph is None:
            await self.reload_graph()
        return self.compiled_graph

    async def reload_graph(self):
        """Rebuilds and recompiles the graph with the latest registry updates."""
        app_logger.info("Reloading Graph...")

        # Build new workflow
        app_logger.debug("Calling build_workflow()...")
        workflow = build_workflow()
        app_logger.debug("build_workflow() done.")

        # One-time setup: Create checkpoint tables using autocommit connection
        # This is required because CREATE INDEX CONCURRENTLY cannot run inside a transaction
        if not GraphService._tables_initialized:
            try:
                app_logger.debug("Initializing checkpoint tables...")
                async with await AsyncConnection.connect(settings.database_url, autocommit=True) as conn:
                    setup_checkpointer = AsyncPostgresSaver(conn)
                    await setup_checkpointer.setup()
                    app_logger.info("LangGraph checkpoint tables initialized.")
                    GraphService._tables_initialized = True
            except Exception as e:
                # Tables might already exist
                app_logger.info(f"Checkpoint setup note: {e}")
                GraphService._tables_initialized = True

        # Create the runtime checkpointer using the pool
        checkpointer = AsyncPostgresSaver(pool)

        # Compile
        app_logger.debug("Compiling graph...")
        self.compiled_graph = workflow.compile(checkpointer=checkpointer, interrupt_before=["qa", "tool_execution"])
        app_logger.info("Graph Reloaded Successfully.")
        return self.compiled_graph
