import asyncio
import os
import sys

# Ensure backend root is in path
# Assuming this script is run from backend/src/tools/
# We need 'src' to be importable as 'src' or add backend to path.
# The imports in the code use 'services.gcp...', so we need 'backend/src' in sys.path?
# Actually, the file imports are `from services.gcp...` which implies python path includes `backend/src`.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from tools.adapter import MCPAdapter

try:
    from mcp.bigquery import mcp as bq_mcp
    from mcp.rag import mcp as rag_mcp
except ImportError:
    # Fallback for direct execution if path issues
    # But since we added ../.. to path, mcp should be found under 'src' -> 'mcp'
    # Wait, 'src' is not a package usually unless __init__.py exists.
    # But imports in this project seem to use `services.xx` which implies `backend/src` IS in path.
    # So `from mcp import ...` should work if `backend/src/mcp` is valid and `backend/src` is in path.
    try:
        from src.mcp.bigquery import mcp as bq_mcp
        from src.mcp.rag import mcp as rag_mcp
    except ImportError:
        # Last resort for local run relative to file
        sys.path.append(os.path.join(os.path.dirname(__file__), "../mcp"))
        import bigquery as bq_module
        import rag as rag_module

        bq_mcp = bq_module.mcp
        rag_mcp = rag_module.mcp


async def test_gcp_tools():
    print("Initializing Adapter with RAG and BigQuery...")
    # Mocking settings if needed for imports to work not failing on missing env vars (since we are just testing definition)
    # The 'mcp' object creation shouldn't trigger checks, only execution.

    adapter = MCPAdapter([rag_mcp, bq_mcp])

    print("Fetching tools...")
    tools = await adapter.get_tools()
    print(f"Found {len(tools)} tools")

    for tool in tools:
        print(f" - {tool.name}: {tool.description}")

    # Check for expected tools
    expected = ["search_knowledge_base", "ingest_file", "run_query", "list_tables"]
    found = [t.name for t in tools]

    missing = [e for e in expected if e not in found]
    if missing:
        print(f"ERROR: Missing tools: {missing}")
    else:
        print("SUCCESS: All expected tools found.")


if __name__ == "__main__":
    asyncio.run(test_gcp_tools())
