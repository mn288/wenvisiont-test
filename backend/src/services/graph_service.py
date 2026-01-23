from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from psycopg import AsyncConnection

from brain.graph import build_workflow
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
        print("Reloading Graph...")

        # Build new workflow
        workflow = build_workflow()

        # One-time setup: Create checkpoint tables using autocommit connection
        # This is required because CREATE INDEX CONCURRENTLY cannot run inside a transaction
        if not GraphService._tables_initialized:
            try:
                async with await AsyncConnection.connect(
                    settings.database_url,
                    autocommit=True
                ) as conn:
                    setup_checkpointer = AsyncPostgresSaver(conn)
                    await setup_checkpointer.setup()
                    print("LangGraph checkpoint tables initialized.")
                    GraphService._tables_initialized = True
            except Exception as e:
                # Tables might already exist
                print(f"Checkpoint setup note: {e}")
                GraphService._tables_initialized = True

        # Create the runtime checkpointer using the pool
        checkpointer = AsyncPostgresSaver(pool)

        # Compile
        self.compiled_graph = workflow.compile(checkpointer=checkpointer, interrupt_before=["qa", "tool_execution"])
        print("Graph Reloaded Successfully.")
        return self.compiled_graph

