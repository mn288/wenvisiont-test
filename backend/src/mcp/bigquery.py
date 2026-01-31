import logging

from fastmcp import FastMCP

from services.gcp.bigquery import execute_sql_with_dryrun, get_schema_embeddings

# Initialize FastMCP server
mcp = FastMCP("gcp-bigquery")
logger = logging.getLogger(__name__)


@mcp.tool()
async def run_query(sql: str) -> str:
    """
    Execute a SQL query against the data warehouse.

    Includes automatic dry-run validation and cost estimation.
    Applies strict read-only limits.

    Args:
        sql: Standarch SQL query (BigQuery dialect).
    """
    try:
        result = await execute_sql_with_dryrun(sql)

        if "error" in result:
            return f"Error executing query: {result['error']}"

        data = result.get("data", [])
        if not data:
            return "Query executed successfully but returned no results."

        # Format as simple table
        # We use a simple markdown formatter to avoid pandas dependency if not present,
        # but pandas is likely there for data work. Safe fallback:
        try:
            import pandas as pd

            df = pd.DataFrame(data)
            return f"Results ({len(data)} rows):\n\n{df.to_markdown(index=False)}"
        except ImportError:
            return f"Results ({len(data)} rows):\n\n{str(data)}"

    except Exception as e:
        logger.error(f"BQ Tool Error: {e}")
        return f"System Error: {str(e)}"


@mcp.tool()
async def list_tables() -> str:
    """List available tables and their schemas."""
    try:
        schemas = await get_schema_embeddings()
        if not schemas:
            return "No tables found."

        output = ""
        for s in schemas:
            output += f"Table: {s['table_id']}\n"
            output += f"Description: {s['description']}\n"
            output += f"Columns: {', '.join([c['name'] for c in s['columns']])}\n\n"

        return output
    except Exception as e:
        return f"Error listing tables: {str(e)}"


if __name__ == "__main__":
    mcp.run()
