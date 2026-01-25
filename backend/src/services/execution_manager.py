import asyncio
from typing import Dict, Optional


class ExecutionManager:
    _instance = None
    _tasks: Dict[str, asyncio.Task] = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ExecutionManager()
        return cls._instance

    def register_task(self, thread_id: str, task: asyncio.Task):
        """Register a background task for a given thread_id."""
        print(f"ExecutionManager: Registering task {id(task)} for thread {thread_id}")
        # Clean up if existing
        if thread_id in self._tasks:
            existing = self._tasks[thread_id]
            if existing.done():
                del self._tasks[thread_id]
        
        # Attach a done callback to auto-remove
        task.add_done_callback(lambda t: self._cleanup(thread_id))
        self._tasks[thread_id] = task

    def cancel_task(self, thread_id: str) -> bool:
        """Cancel the task associated with thread_id."""
        print(f"ExecutionManager: Attempting to cancel thread {thread_id}")
        task = self._tasks.get(thread_id)
        if task:
            if not task.done():
                print(f"ExecutionManager: Cancelling running task {id(task)} for thread {thread_id}")
                task.cancel()
                return True
            else:
                print(f"ExecutionManager: Task {id(task)} for thread {thread_id} is already done.")
        else:
             print(f"ExecutionManager: No task found for thread {thread_id}")
        return False

    def get_task(self, thread_id: str) -> Optional[asyncio.Task]:
        return self._tasks.get(thread_id)

    def _cleanup(self, thread_id: str):
        """Internal cleanup callback."""
        if thread_id in self._tasks:
            del self._tasks[thread_id]
