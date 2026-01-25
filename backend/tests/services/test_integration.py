import asyncio

import pytest
from fastmcp import FastMCP

from tools.adapter import MCPAdapter


@pytest.mark.asyncio
async def test_integration():
    # 1. Setup Local Mock MCP Server
    print("Initializing Local Mock MCP Server...")
    mcp = FastMCP("test-server")

    @mcp.tool()
    async def search_web(query: str) -> str:
        """Mock search for testing integration."""
        return f"Mock search result for: {query}"

    print("Initializing Adapter...")
    adapter = MCPAdapter([mcp])

    print("Fetching tools...")
    tools = await adapter.get_tools()
    print(f"Found {len(tools)} tools")

    for tool in tools:
        print(f" - {tool.name}: {tool.description}")

    search_tool = next((t for t in tools if t.name == "search_web"), None)
    if search_tool:
        print("\nTesting 'search_web' tool...")
        # Test async invocation
        try:
            # CrewAI BaseTool uses arun for async
            result = await search_tool.arun(query="FastMCP Integration")
            print(f"Result (async): {result}")
            assert "Mock search result" in str(result)
        except Exception as e:
            pytest.fail(f"Error invoking tool async: {e}")

        # Test sync invocation (should also work via wrapper)
        try:
            # CrewAI BaseTool uses run for sync
            result_sync = search_tool.run(query="FastMCP Integration Sync")
            print(f"Result (sync): {result_sync}")
            assert "Mock search result" in str(result_sync)
        except Exception as e:
            pytest.fail(f"Error invoking tool sync: {e}")
    else:
        pytest.fail("search_web tool not found!")


if __name__ == "__main__":
    asyncio.run(test_integration())
