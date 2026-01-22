from contextlib import asynccontextmanager
from functools import partial

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph
from langgraph.types import Send
from psycopg_pool import AsyncConnectionPool

from brain.nodes import (
    execute_agent_node,
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
    registry = AgentRegistry()
    workflow = StateGraph(GraphState)

    workflow.add_node("preprocess", preprocess_node)
    # workflow.add_node("router", router_node) # Deprecated
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("tool_planning", tool_planning_node)
    workflow.add_node("tool_execution", tool_execution_node)
    workflow.add_node("qa", qa_node)

    # Dynamic Nodes
    # We get a fresh list of agents from the registry
    for node_config in registry.get_all():
        workflow.add_node(node_config.name, partial(execute_agent_node, agent_name=node_config.name))
        workflow.add_edge(node_config.name, "supervisor")

    workflow.set_entry_point("preprocess")

    # Direct to supervisor (skip legacy router)
    workflow.add_conditional_edges("preprocess", route_preprocess)

    # Construct supervisor mapping
    supervisor_map = {
        "tools": "tool_planning",
        "qa": "qa",
    }
    # Add dynamic agents to map
    for node_config in registry.get_all():
        supervisor_map[node_config.name] = node_config.name

    workflow.add_conditional_edges(
        "supervisor",
        supervisor_decision,
        supervisor_map,
    )

    workflow.add_edge("tool_planning", "tool_execution")
    workflow.add_edge("tool_execution", "supervisor")
    workflow.add_edge("qa", END)

    return workflow


# Direct to supervisor (skip legacy router)
def route_preprocess(state: GraphState):
    """Route after preprocessing."""
    if state.get("errors"):
        return END
    return "supervisor"


def supervisor_decision(state: GraphState):
    next_steps = state.get("next_step", [])
    if not next_steps:
        return "qa"

    # If list (parallel support via Send)
    if isinstance(next_steps, list):
        # If single item, return string to use standard edge
        if len(next_steps) == 1:
            return next_steps[0]

        # Parallel execution using Send
        # We send the same state to all chosen agents
        return [Send(node, state) for node in next_steps]

    return next_steps  # Fallback if string


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
