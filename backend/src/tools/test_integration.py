import asyncio

from src.tools.adapter import MCPAdapter
from src.tools.server import mcp


async def test_integration():
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
            result = await search_tool.ainvoke({"query": "FastMCP Integration"})
            print(f"Result (async): {result}")
        except Exception as e:
            print(f"Error invoking tool async: {e}")

        # Test sync invocation (should also work via wrapper)
        try:
            result_sync = search_tool.invoke({"query": "FastMCP Integration Sync"})
            print(f"Result (sync): {result_sync}")
        except Exception as e:
            print(f"Error invoking tool sync: {e}")
    else:
        print("search_web tool not found!")


if __name__ == "__main__":
    asyncio.run(test_integration())
