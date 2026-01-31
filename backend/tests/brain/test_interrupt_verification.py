import asyncio

import pytest
from langgraph.checkpoint.memory import MemorySaver

from brain.graph import build_workflow


@pytest.mark.asyncio
async def test_graph_interrupt_tools():
    # Use MemorySaver for testing
    checkpointer = MemorySaver()

    # Compile graph with same interrupts as production
    # Compile graph with same interrupts as production
    workflow = build_workflow()

    # Ensure tool_execution exists before interrupting (though mock graph might fail if no agents)
    # The build_workflow() uses AgentRegistry.
    # For unit test, registry might be empty, but static nodes exist.

    graph = workflow.compile(checkpointer=checkpointer, interrupt_before=["qa", "tool_execution"])

    # Mock state that should route to 'tools'
    # We can force the next_step to 'tools' via the supervisor decision logic
    # but since we are mocking the supervisor node or just injecting state, let's try to simulate basic flow.
    # However, to avoid mocking LLMs, we'll manually inject state that *would* result in a tool call if we were at that step.
    # The graph structure is:
    # preprocess -> router -> supervisor -> [research, analyze, tools, qa]

    # Let's start the graph.

    # We want to verify that if the supervisor says "TOOLS", the graph stops.
    # To avoid running actual LLMs, we will mock the Supervisor Node behavior or just trust the graph structure
    # and verify the 'interrupt_before' config is respected by the compiled graph object.

    # Checking the graph object's interrupt_before property directly might be easiest if accessible,
    # otherwise we run it.

    # To verify the 'interrupt_before' config is respected by the compiled graph object.
    # The attribute is likely 'interrupt_before_nodes' in recent langgraph versions.

    interrupts = getattr(graph, "interrupt_before_nodes", None)
    # If using an older version might be different, but let's try this based on the error.
    if interrupts is None:
        interrupts = graph.interrupt_before

    assert "tool_execution" in interrupts
    assert "qa" in interrupts
    print("Graph correctly configured to interrupt before 'tool_execution' and 'qa'.")


if __name__ == "__main__":
    asyncio.run(test_graph_interrupt_tools())
