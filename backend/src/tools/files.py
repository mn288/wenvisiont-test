import asyncio
import os
from typing import Type

import aiofiles
from aiofiles import os as aios
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class FileReadSchema(BaseModel):
    file_path: str = Field(..., description="The absolute or relative path to the file to read.")


class AsyncFileReadTool(BaseTool):
    name: str = "Read File (Async)"
    description: str = "Reads the content of a file from the local workspace asynchronously."
    args_schema: Type[BaseModel] = FileReadSchema
    root_dir: str = Field(default=None, exclude=True)

    def __init__(self, root_dir: str = None, **kwargs):
        super().__init__(**kwargs)
        self.root_dir = root_dir

    def _get_safe_path(self, file_path: str) -> str:
        if not self.root_dir:
            raise ValueError("Root directory not configured for file access.")

        # Resolve absolute path
        abs_root = os.path.abspath(self.root_dir)
        # Join and resolve
        target_path = os.path.abspath(os.path.join(abs_root, file_path))

        # Check traversal
        if not target_path.startswith(abs_root):
            raise ValueError("Access denied: Path is outside the sandbox.")

        return target_path

    def _run(self, file_path: str) -> str:
        """Read file synchronously (wrapper around async)."""
        try:
            loop = asyncio.get_running_loop()
            # If already in a loop, we can't block it with run_until_complete
            # If we are in LangGraph/FastAPI, we shouldn't be calling this sync method anyway if properly awaited.
            # But CrewAI agents might call .run() if they think the tool is sync.
            # For checking if loop is running:
            if loop.is_running():
                # We are in trouble if we block here.
                # Ideally, CrewAI agents should use `arun`.
                # Fallback: Raise error telling agent to use async or return a future?
                # Actually, `aiofiles` is async. If we need sync capability fallback, we should use `open()`.
                return self._run_sync(file_path)
            else:
                return loop.run_until_complete(self._arun(file_path))
        except RuntimeError:
            return asyncio.run(self._arun(file_path))

    def _run_sync(self, file_path: str) -> str:
        """Fallback for sync execution."""
        try:
            full_path = self._get_safe_path(file_path)
        except ValueError as e:
            return str(e)

        if not os.path.exists(full_path):
            return f"Error: File not found: {file_path}"

        try:
            with open(full_path, "r") as f:
                content = f.read()
            return content
        except Exception as e:
            return f"Error reading file: {str(e)}"

    async def _arun(self, file_path: str) -> str:
        try:
            full_path = self._get_safe_path(file_path)
        except ValueError as e:
            return str(e)

        
        # Check existence async
        try:
           # aiofiles.os.path.exists is available in recent versions, but fallback to stat for safety
           await aios.stat(full_path)
           exists = True
        except OSError:
           exists = False

        if not exists:
             return f"Error: File not found: {file_path}"

        try:
            async with aiofiles.open(full_path, mode="r") as f:
                content = await f.read()
            return content
        except Exception as e:
            return f"Error reading file: {str(e)}"


class FileWriteSchema(BaseModel):
    file_path: str = Field(..., description="The absolute or relative path to the file to write.")
    content: str = Field(..., description="The content to write to the file.")
    append: bool = Field(False, description="Whether to append to the file instead of overwriting.")


class AsyncFileWriteTool(BaseTool):
    name: str = "Write File (Async)"
    description: str = "Writes content to a file in the local workspace asynchronously."
    args_schema: Type[BaseModel] = FileWriteSchema
    root_dir: str = Field(default=None, exclude=True)

    def __init__(self, root_dir: str = None, **kwargs):
        super().__init__(**kwargs)
        self.root_dir = root_dir

    def _get_safe_path(self, file_path: str) -> str:
        if not self.root_dir:
            raise ValueError("Root directory not configured for file access.")

        abs_root = os.path.abspath(self.root_dir)
        target_path = os.path.abspath(os.path.join(abs_root, file_path))

        if not target_path.startswith(abs_root):
            raise ValueError("Access denied: Path is outside the sandbox.")

        return target_path

    def _run(self, file_path: str, content: str, append: bool = False) -> str:
        """Write file synchronously (wrapper around async)."""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                return self._run_sync(file_path, content, append)
            else:
                return loop.run_until_complete(self._arun(file_path, content, append))
        except RuntimeError:
            return asyncio.run(self._arun(file_path, content, append))

    def _run_sync(self, file_path: str, content: str, append: bool = False) -> str:
        try:
            full_path = self._get_safe_path(file_path)
        except ValueError as e:
            return str(e)

        mode = "a" if append else "w"
        try:
            directory = os.path.dirname(full_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            with open(full_path, mode=mode) as f:
                f.write(content)
            print(f"DEBUG: AsyncFileWriteTool (Sync Fallback) wrote to: {full_path}")

            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

    async def _arun(self, file_path: str, content: str, append: bool = False) -> str:
        try:
            full_path = self._get_safe_path(file_path)
        except ValueError as e:
            return str(e)

        from aiofiles import os as aios
        mode = "a" if append else "w"
        try:
            # ensure dir exists
            directory = os.path.dirname(full_path)
            # Check dir async
            try:
                 await aios.stat(directory)
            except OSError:
                 await aios.makedirs(directory, exist_ok=True)

            async with aiofiles.open(full_path, mode=mode) as f:
                await f.write(content)
            print(f"DEBUG: AsyncFileWriteTool wrote to: {full_path}")

            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"
