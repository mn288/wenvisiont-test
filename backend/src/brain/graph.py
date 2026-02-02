from contextlib import asynccontextmanager
from functools import partial

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph
from psycopg_pool import AsyncConnectionPool

from brain.logger import app_logger
from brain.nodes import (
    execute_agent_node,
    execute_workflow_node,
    preprocess_node,
    qa_node,
    supervisor_node,
    tool_execution_node,
    tool_planning_node,
)
from brain.registry import AgentRegistry
from core.config import settings
from models.state import GraphState


def build_workflow() -> StateGraph:
    """
    Builds and returns a new StateGraph instance based on the current AgentRegistry.
    This allows for dynamic reloading of agents.
    """
    app_logger.debug("Inside build_workflow start")
    registry = AgentRegistry()
    workflow = StateGraph(GraphState)

    workflow.add_node("preprocess", preprocess_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("tool_planning", tool_planning_node)
    workflow.add_node("tool_execution", tool_execution_node)
    workflow.add_node("qa", qa_node)

    RESERVED_NAMES = {"supervisor", "tool_planning", "tool_execution", "qa", "preprocess"}

    app_logger.debug(f"Adding {len(registry.get_all())} agents...")
    # Dynamic Nodes (Atomic Agents)
    # We get a fresh list of agents from the registry
    for node_config in registry.get_all():
        if node_config.name in RESERVED_NAMES:
            app_logger.debug(f"Skipping reserved agent name '{node_config.name}'")
            continue

        workflow.add_node(node_config.name, partial(execute_agent_node, agent_name=node_config.name))
        workflow.add_edge(node_config.name, "supervisor")

    app_logger.debug(f"Adding {len(registry.get_workflows())} workflows...")
    # Dynamic Nodes (Superagent Teams / Workflows)
    for wf in registry.get_workflows():
        if wf.name in RESERVED_NAMES:
            app_logger.debug(f"Skipping reserved workflow name '{wf.name}'")
            continue

        workflow.add_node(wf.name, partial(execute_workflow_node, workflow_name=wf.name))
        workflow.add_edge(wf.name, "supervisor")

    workflow.set_entry_point("preprocess")

    workflow.add_conditional_edges("preprocess", route_preprocess)

    workflow.add_edge("tool_planning", "tool_execution")
    workflow.add_edge("tool_execution", "supervisor")
    workflow.add_edge("qa", END)

    app_logger.debug("build_workflow returning")
    return workflow


# Direct to supervisor
def route_preprocess(state: GraphState):
    """Route after preprocessing."""
    if state.get("errors"):
        return END
    return "supervisor"


# Helper to get the compiled graph with checkpointer (Legacy / Testing)
@asynccontextmanager
async def get_graph():
    # Helper context manager to handle DB connection
    connection_string = settings.database_url

    async with AsyncConnectionPool(conninfo=connection_string, open=False) as pool:
        await pool.open()
        checkpointer = AsyncPostgresSaver(pool)

        # Ensure checkpoint tables exist
        await checkpointer.setup()

        # Compile the graph with checkpointer and interrupt
        workflow = build_workflow()
        graph = workflow.compile(checkpointer=checkpointer, interrupt_before=["qa", "tool_execution"])
        yield graph
