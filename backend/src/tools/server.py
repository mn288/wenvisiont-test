from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("demo-tools")


@mcp.tool()
def search_web(query: str) -> str:
    """Mock search tool for demonstration."""
    return f"Mock search results for: {query}"


@mcp.tool()
def analyze_data(data: str) -> str:
    """Mock data analysis tool."""
    return f"Analysis complete for: {data}"


if __name__ == "__main__":
    mcp.run()
