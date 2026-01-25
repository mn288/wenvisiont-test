import io
import orjson
import polars as pl
from fastapi import FastAPI

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
# Initialize FastMCP Server
# Initialize FastMCP Server

mcp = FastMCP("analysis", dependencies=["polars", "orjson"], host="0.0.0.0")
mcp_app = mcp.sse_app()
app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "ok"}


app.mount("/", mcp_app)


@mcp.tool()
def search_web(query: str) -> str:
    """Mock search tool for demonstration."""
    # In a real app, this would call Serper or similar.
    # The user had this as a mock in server.py, so maintaining behavior.
    return f"Mock search results for: {query}"


@mcp.tool()
def analyze_data(data: str) -> str:
    """
    Analyze data using Polars.
    Accepts JSON (list of dicts) or CSV string.
    Returns statistical summary.
    """
    try:
        # Try JSON first
        try:
            # Check if valid JSON structure
            json_obj = orjson.loads(data)
            df = pl.DataFrame(json_obj)
        except orjson.JSONDecodeError:
            # Try CSV
            df = pl.read_csv(io.StringIO(data))

        if df.is_empty():
            return "Data is empty."

        # Generate summary
        summary = df.describe()
        return f"Data Analysis Summary:\\n\\n{summary}"

    except Exception as e:
        return f"Failed to analyze data: {str(e)}"


if __name__ == "__main__":
    mcp.run()
