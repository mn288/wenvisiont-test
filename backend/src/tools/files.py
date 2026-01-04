import os
from typing import Type

import aiofiles
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

    async def _run(self, file_path: str) -> str:
        """Read file asynchronously."""
        return await self._arun(file_path)

    async def _arun(self, file_path: str) -> str:
        try:
            full_path = self._get_safe_path(file_path)
        except ValueError as e:
            return str(e)

        if not os.path.exists(full_path):
            return f"Error: File {file_path} does not exist."
        try:
            async with aiofiles.open(file_path, mode="r") as f:
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

    async def _run(self, file_path: str, content: str, append: bool = False) -> str:
        return await self._arun(file_path, content, append)

    async def _arun(self, file_path: str, content: str, append: bool = False) -> str:
        try:
            full_path = self._get_safe_path(file_path)
        except ValueError as e:
            return str(e)

        mode = "a" if append else "w"
        try:
            # ensure dir exists
            directory = os.path.dirname(full_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            async with aiofiles.open(full_path, mode=mode) as f:
                await f.write(content)
            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"
