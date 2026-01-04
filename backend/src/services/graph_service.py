from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph

from src.brain.graph import build_workflow
from src.core.database import pool


class GraphService:
    _instance = None

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

        # Setup Checkpointer
        # We use the global connection pool
        checkpointer = AsyncPostgresSaver(pool)

        # Checkpointer setup is idempotent (creates tables if not exists)
        # We ensure tables exist
        await checkpointer.setup()

        # Compile
        self.compiled_graph = workflow.compile(checkpointer=checkpointer, interrupt_before=["qa", "tool_execution"])
        print("Graph Reloaded Successfully.")
        return self.compiled_graph
