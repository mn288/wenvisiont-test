import asyncio
import json

from fastmcp import Client

from tools.server import mcp


async def inspect():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        print(f"Found {len(tools)} tools")
        for tool in tools:
            print(f"\nTool: {tool.name}")
            print(f"Description: {tool.description}")
            print("Schema:")
            print(json.dumps(tool.inputSchema, indent=2))


if __name__ == "__main__":
    asyncio.run(inspect())
