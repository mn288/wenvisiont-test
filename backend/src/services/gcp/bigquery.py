"""
BigQuery Text-to-SQL integration with mandatory dry-run validation.
Implements Pattern B from AWP: Verified Analytical Query (Structured Data).

Key security features:
- Mandatory dry-run validation before execution
- Read-Only service account enforcement (at IAM level)
- Billing limit enforcement
- Query cost estimation
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_bq_client = None


def _get_settings():
    """Lazy import of settings to avoid circular imports."""
    from core.config import settings

    return settings


def get_bq_client():
    """
    Lazy initialization of BigQuery client.
    """
    global _bq_client
    settings = _get_settings()

    if _bq_client is None and settings.GCP_PROJECT_ID:
        try:
            from google.cloud import bigquery

            _bq_client = bigquery.Client(project=settings.GCP_PROJECT_ID)
            logger.info("BigQuery client initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize BigQuery client: {e}")
            _bq_client = None

    return _bq_client


async def execute_sql_with_dryrun(
    sql: str,
    max_bytes_billed: int = 1_000_000_000,  # 1GB default limit
    parameters: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Execute a SQL query with mandatory dry-run validation.

    This implements the AWP Pattern B security model:
    1. Dry run to validate syntax and estimate costs
    2. Check against billing limits
    3. Execute with Read-Only SA (enforced at IAM level)

    Args:
        sql: SQL query to execute
        max_bytes_billed: Maximum bytes allowed for billing (default 1GB)
        parameters: Optional query parameters

    Returns:
        Query results or error information

    Example:
        ```python
        result = await execute_sql_with_dryrun(
            "SELECT * FROM sales WHERE region = @region",
            parameters=[{"name": "region", "type": "STRING", "value": "EU"}]
        )
        ```
    """
    settings = _get_settings()

    if not settings.GCP_PROJECT_ID:
        return {"error": "GCP_PROJECT_ID not configured"}

    if not settings.BIGQUERY_DATASET:
        return {"error": "BIGQUERY_DATASET not configured"}

    client = get_bq_client()
    if not client:
        return {"error": "BigQuery client not available"}

    from google.cloud import bigquery

    # Build job config
    job_config = bigquery.QueryJobConfig(
        dry_run=True,
        use_query_cache=False,
    )

    # Add parameters if provided
    if parameters:
        job_config.query_parameters = [
            bigquery.ScalarQueryParameter(p["name"], p["type"], p["value"]) for p in parameters
        ]

    # =========================================================================
    # Step 1: DRY RUN VALIDATION
    # =========================================================================
    try:
        dry_run_job = client.query(sql, job_config=job_config)
        bytes_processed = dry_run_job.total_bytes_processed or 0

        # Estimate cost (as of 2024: $5 per TB)
        estimated_cost_usd = (bytes_processed / 1e12) * 5

        logger.info(f"Dry run OK: {bytes_processed / 1e6:.2f} MB estimated, ~${estimated_cost_usd:.4f} USD")

        # Check billing limit
        if bytes_processed > max_bytes_billed:
            return {
                "error": "Query exceeds billing limit",
                "bytes_estimated": bytes_processed,
                "limit": max_bytes_billed,
                "estimated_cost_usd": estimated_cost_usd,
                "sql": sql,
            }

    except Exception as e:
        error_msg = str(e)
        logger.warning(f"Dry run failed: {error_msg}")
        return {
            "error": f"Dry run validation failed: {error_msg}",
            "sql": sql,
        }

    # =========================================================================
    # Step 2: EXECUTE QUERY
    # =========================================================================
    try:
        # Reset job config for actual execution
        exec_config = bigquery.QueryJobConfig(
            maximum_bytes_billed=max_bytes_billed,
        )

        if parameters:
            exec_config.query_parameters = [
                bigquery.ScalarQueryParameter(p["name"], p["type"], p["value"]) for p in parameters
            ]

        query_job = client.query(sql, job_config=exec_config)
        results = query_job.result()

        # Convert to list of dicts
        rows = [dict(row) for row in results]

        return {
            "data": rows,
            "row_count": len(rows),
            "bytes_processed": query_job.total_bytes_processed,
            "cache_hit": query_job.cache_hit,
            "slot_millis": query_job.slot_millis,
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Query execution failed: {error_msg}")
        return {
            "error": f"Query execution failed: {error_msg}",
            "sql": sql,
        }


async def get_schema_embeddings(
    dataset_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get table schemas for Few-Shot examples in Text-to-SQL.

    Returns schema information suitable for embedding and
    similarity search when generating SQL queries.

    Args:
        dataset_id: Dataset to describe (uses default if not provided)

    Returns:
        List of table schema descriptions
    """
    settings = _get_settings()
    client = get_bq_client()

    if not client:
        return []

    target_dataset = dataset_id or settings.BIGQUERY_DATASET
    if not target_dataset:
        return []

    try:
        dataset_ref = client.dataset(target_dataset)
        tables = list(client.list_tables(dataset_ref))

        schemas = []
        for table_item in tables:
            table = client.get_table(table_item.reference)

            # Build schema description
            columns = []
            for field in table.schema:
                columns.append(
                    {
                        "name": field.name,
                        "type": field.field_type,
                        "mode": field.mode,
                        "description": field.description or "",
                    }
                )

            schemas.append(
                {
                    "table_id": table.table_id,
                    "full_name": f"{table.project}.{table.dataset_id}.{table.table_id}",
                    "description": table.description or "",
                    "row_count": table.num_rows,
                    "columns": columns,
                    "schema_text": _format_schema_for_embedding(table),
                }
            )

        return schemas

    except Exception as e:
        logger.error(f"Failed to get schemas: {e}")
        return []


def _format_schema_for_embedding(table) -> str:
    """Format table schema as text for embedding."""
    lines = [
        f"Table: {table.table_id}",
        f"Description: {table.description or 'No description'}",
        f"Rows: {table.num_rows}",
        "Columns:",
    ]

    for field in table.schema:
        desc = f" - {field.description}" if field.description else ""
        lines.append(f"  - {field.name} ({field.field_type}){desc}")

    return "\n".join(lines)


async def validate_sql_syntax(sql: str) -> Dict[str, Any]:
    """
    Validate SQL syntax without executing.

    Args:
        sql: SQL query to validate

    Returns:
        Validation result with any syntax errors
    """
    _get_settings()
    client = get_bq_client()

    if not client:
        return {"valid": False, "error": "BigQuery client not available"}

    from google.cloud import bigquery

    job_config = bigquery.QueryJobConfig(
        dry_run=True,
        use_query_cache=False,
    )

    try:
        client.query(sql, job_config=job_config)
        return {"valid": True}
    except Exception as e:
        return {"valid": False, "error": str(e)}
