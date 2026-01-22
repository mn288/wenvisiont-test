import asyncio

# Mocking modules before import
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from brain.nodes import execute_agent_node
from models.infrastructure import InfrastructureConfig

# Create mocks for database pool and logger
mock_pool = MagicMock()

# Setup Pool Context Manager
pool_conn_ctx = MagicMock()
mock_pool.connection.return_value = pool_conn_ctx
conn_mock = MagicMock()
pool_conn_ctx.__aenter__ = AsyncMock(return_value=conn_mock)
pool_conn_ctx.__aexit__ = AsyncMock()

# Setup Cursor Context Manager
cursor_ctx = MagicMock()
conn_mock.cursor.return_value = cursor_ctx
cursor_mock = MagicMock()
cursor_ctx.__aenter__ = AsyncMock(return_value=cursor_mock)
cursor_ctx.__aexit__ = AsyncMock()

# Setup Execute and Commit
cursor_mock.execute = AsyncMock()
conn_mock.commit = AsyncMock()

# Patching dependencies
sys.modules["core.database"] = MagicMock()
sys.modules["core.database"].pool = mock_pool


async def test_pii_masking_and_metadata():
    print("Starting PII Masking and Metadata Verification...")

    # 1. Setup Mock Config
    config = {"configurable": {"thread_id": "test_thread_123", "checkpoint_id": "chk_1"}}

    # 2. Setup Mock State
    state = {"input_request": "Execute task", "context": "Previous context", "results": []}

    # 3. Setup Mocks for Services
    # We need to mock crew_service and infrastructure_service inside nodes.py
    # Since they are instantiated at module level in nodes.py, we need to patch them there.
    from brain import nodes

    # Mock Infrastructure Service
    nodes.infrastructure_service = MagicMock()
    # Explicitly patch the pool in nodes module to avoid real DB connection
    nodes.pool = mock_pool

    nodes.infrastructure_service.get_or_create_infrastructure.return_value = InfrastructureConfig(
        id="infra_1",
        status="ready",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        config={},
        local_workspace_path="/tmp/test_workspace",
    )

    # Mock Crew Service Result
    mock_result = MagicMock()
    # Simulate PII in output
    mock_result.summary = "My email is test@example.com and phone is 06 12 34 56 78."
    mock_result.raw_output = "Raw output with test@example.com"
    mock_result.metadata = {"model": "gpt-4", "usage": {"total_tokens": 100}}
    mock_result.model_dump.return_value = {
        "task_id": "task_1",
        "summary": mock_result.summary,
        "raw_output": mock_result.raw_output,
        "metadata": mock_result.metadata,
    }

    nodes.crew_service = MagicMock()
    nodes.crew_service.execute_task = AsyncMock(return_value=mock_result)

    # 4. Run the Node
    print("Executing 'execute_agent_node'...")
    node_result = await execute_agent_node(state, config, "test_agent")

    # 5. Verify Output Masking
    print("\nVerifying Output...")
    results = node_result["results"][0]

    summary = results["summary"]
    raw = results["raw_output"]

    print(f"Original Summary: {mock_result.summary}")
    print(f"Masked Summary:   {summary}")

    if "[EMAIL_REDACTED]" in summary and "[PHONE_REDACTED]" in summary:
        print("✅ PII Masking: PASSED (Summary)")
    else:
        print("❌ PII Masking: FAILED (Summary)")

    if "[EMAIL_REDACTED]" in raw:
        print("✅ PII Masking: PASSED (Raw Output)")
    else:
        print("❌ PII Masking: FAILED (Raw Output)")

    # 6. Verify Log Calls (Metadata)
    # We need to inspect the calls to the mock_pool (since Logger uses pool)
    # But checking SQL parameters on a MagicMock chain is hard.
    # Instead, we can monkeypatch LogHandler.log_step

    print("\nVerifying Logger Calls...")
    # Since we can't easily patch the class instance inside the function after import,
    # we will rely on checking if the function ran without error and maybe print mock calls if possible.
    # Actually, a better way for this specific test is to check if execute_agent_node
    # passed the metadata to the logger.

    # Let's inspect the `nodes.crew_service.execute_task` return value propagation
    # The logging happens locally in the function.

    # We can inspect `mock_pool` calls to `execute`
    # The params should contain the metadata JSON string

    calls = mock_pool.connection.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value.execute.call_args_list

    metadata_found = False
    for call in calls:
        query, params = call[0]
        # params: (thread_id, step_name, log_type, content, created_at, checkpoint_id, metadata_json)
        # metadata_json is the last one
        meta_json = params[6]
        if meta_json and '"total_tokens": 100' in meta_json:
            metadata_found = True
            print(f"✅ Metadata Logging Found: {meta_json}")
            break

    if not metadata_found:
        print("❌ Metadata Logging: FAILED (Could not find expected metadata in DB insert calls)")
        # Print all calls for debug
        # for i, call in enumerate(calls):
        #     print(f"Call {i} params: {call[0][1]}")


if __name__ == "__main__":
    asyncio.run(test_pii_masking_and_metadata())
