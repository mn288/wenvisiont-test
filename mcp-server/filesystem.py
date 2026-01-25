import os
import aiofiles
from aiofiles import os as aios
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP


# Initialize FastMCP Server

mcp = FastMCP("filesystem", dependencies=["aiofiles"], host="0.0.0.0")
mcp_app = mcp.sse_app()
app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "ok"}


app.mount("/", mcp_app)


# Configuration for secure path access
# In Docker, we default to /data or similar, ensuring we don't expose sensitive host OS files
# The container should create a volume mapped to this ROOT_DIR
ROOT_DIR = os.getenv("FILESYSTEM_ROOT", "/app/data")

# Create root dir if not exists
if not os.path.exists(ROOT_DIR):
    os.makedirs(ROOT_DIR, exist_ok=True)


def _get_safe_path(file_path: str) -> str:
    """Validate and resolve path to ensure it remains within ROOT_DIR."""
    abs_root = os.path.abspath(ROOT_DIR)
    target_path = os.path.abspath(os.path.join(abs_root, file_path))

    if not target_path.startswith(abs_root):
        raise ValueError("Access denied: Path is outside the sandbox.")

    return target_path


@mcp.tool()
async def read_file(file_path: str) -> str:
    """
    Read the content of a file from the local workspace.
    Args:
        file_path: Relative path to the file.
    """
    try:
        full_path = _get_safe_path(file_path)

        # Check existence async
        try:
            await aios.stat(full_path)
        except OSError:
            return f"Error: File not found: {file_path}"

        async with aiofiles.open(full_path, mode="r") as f:
            content = await f.read()
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"


@mcp.tool()
async def write_file(file_path: str, content: str) -> str:
    """
    Write content to a file in the local workspace.
    Args:
        file_path: Relative path to the file.
        content: The text content to write.
    """
    try:
        full_path = _get_safe_path(file_path)

        # Ensure dir exists
        directory = os.path.dirname(full_path)
        try:
            await aios.stat(directory)
        except OSError:
            await aios.makedirs(directory, exist_ok=True)

        async with aiofiles.open(full_path, mode="w") as f:
            await f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@mcp.tool()
async def list_directory(directory_path: str = ".") -> str:
    """
    List files in a directory.
    Args:
        directory_path: Relative path to the directory (default: root)
    """
    try:
        full_path = _get_safe_path(directory_path)

        if not os.path.isdir(full_path):
            return f"Error: Not a directory: {directory_path}"

        items = os.listdir(
            full_path
        )  # aiofiles doesn't have listdir, using sync os for directory listing is generally fast enough or use scandir
        return "\n".join(items)
    except Exception as e:
        return f"Error listing directory: {str(e)}"


if __name__ == "__main__":
    mcp.run()
