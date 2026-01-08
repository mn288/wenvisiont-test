import asyncio
import os
import shutil

from tools.files import AsyncFileWriteTool


def test_sync_execution():
    print("Testing Synchronous Execution...")
    workspace = "/tmp/test_workspace_sync"
    if os.path.exists(workspace):
        shutil.rmtree(workspace)
    os.makedirs(workspace)

    tool = AsyncFileWriteTool(root_dir=workspace)

    try:
        # CrewAI agents in sync mode call .run()
        # If _run is async, this returns a coroutine and does NOT execute
        result = tool.run(file_path="test_sync.txt", content="Hello Sync")
        print(f"Result type: {type(result)}")
        print(f"Result value: {result}")

        if os.path.exists(os.path.join(workspace, "test_sync.txt")):
            print("SUCCESS: File created in sync mode.")
        else:
            print("FAILURE: File NOT created in sync mode.")
            if asyncio.iscoroutine(result):
                print("Confirmed: Result is a coroutine.")
                # Clean up coroutine to avoid runtime warning
                asyncio.run(result)
    except Exception as e:
        print(f"Error in sync execution: {e}")


async def test_async_execution():
    print("\nTesting Async Execution...")
    workspace = "/tmp/test_workspace_async"
    if os.path.exists(workspace):
        shutil.rmtree(workspace)
    os.makedirs(workspace)

    tool = AsyncFileWriteTool(root_dir=workspace)

    try:
        # CrewAI agents in async mode call .run() but await it?
        # Or they verify is_coroutine_function?
        # Typically they assume _run is sync block.
        result = await tool._arun(file_path="test_async.txt", content="Hello Async")
        print(f"Result: {result}")

        if os.path.exists(os.path.join(workspace, "test_async.txt")):
            print("SUCCESS: File created in async mode.")
        else:
            print("FAILURE: File NOT created in async mode.")
    except Exception as e:
        print(f"Error in async execution: {e}")


if __name__ == "__main__":
    test_sync_execution()
    asyncio.run(test_async_execution())
