import asyncio
from typing import Any, Callable, Dict, List, Optional, Type, Union

from crewai.tools import BaseTool
from fastmcp import Client, FastMCP
from pydantic import BaseModel, PrivateAttr, create_model
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from brain.logger import app_logger

# Check if MCPServerConfig is available, if not use Dict or define locally for typing
try:
    from models.mcp import MCPServerConfig
except ImportError:
    MCPServerConfig = Any

# Apply nest_asyncio to allow re-entrant event loops (Critical for FastAPI + CrewAI tools)
# Note: nest_asyncio does NOT support uvloop, which uvicorn uses by default.
# We defer application to runtime when a loop is available and it's not uvloop.
import nest_asyncio


def _safe_apply_nest_asyncio(loop=None):
    """
    Safely apply nest_asyncio only if the loop is not uvloop.
    uvloop is incompatible with nest_asyncio.
    """
    try:
        if loop is None:
            loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, nothing to patch
        return False

    loop_type = type(loop).__name__
    if "uvloop" in loop_type.lower():
        # uvloop doesn't support nest_asyncio patching
        return False

    try:
        nest_asyncio.apply(loop)
        return True
    except ValueError:
        # Already patched or incompatible
        return False


def _json_schema_to_pydantic(name: str, schema: Dict[str, Any]) -> Type[BaseModel]:
    """
    Convert a JSON schema to a Pydantic model dynamically.
    Refined to handle more complex nested structures if needed in future.
    """
    fields = {}
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    for field_name, field_info in properties.items():
        field_type = str  # Default to string
        t = field_info.get("type", "string")
        if t == "integer":
            field_type = int
        elif t == "number":
            field_type = float
        elif t == "boolean":
            field_type = bool
        elif t == "array":
            field_type = List[Any]
        elif t == "object":
            field_type = Dict[str, Any]

        # Determine if required
        if field_name in required:
            fields[field_name] = (field_type, ...)
        else:
            fields[field_name] = (Optional[field_type], None)

    return create_model(f"{name}Schema", **fields)


# Define a custom tool class that inherits from CrewAI's BaseTool
class CrewMCPTool(BaseTool):
    name: str
    description: str
    args_schema: Type[BaseModel]
    _sync_tool_func: Callable = PrivateAttr()
    _async_tool_func: Callable = PrivateAttr()

    def __init__(self, sync_tool_func: Callable, async_tool_func: Callable, **data):
        super().__init__(**data)
        self._sync_tool_func = sync_tool_func
        self._async_tool_func = async_tool_func

    def _run(self, *args, **kwargs):
        """
        Execute the tool synchronously.
        Delegates to the sync wrapper.
        """
        return self._sync_tool_func(*args, **kwargs)

    async def _arun(self, *args, **kwargs):
        """Execute the tool asynchronously."""
        return await self._async_tool_func(*args, **kwargs)


class MCPAdapter:
    def __init__(self, servers: List[Union[FastMCP, MCPServerConfig]]):
        """
        Initialize with a list of servers.
        """
        self.servers = servers
        self.clients = {}  # Cache for reusable clients

    def _get_cached_client(self, server_conf):
        """Get or create a cached client."""
        # Identification key
        if isinstance(server_conf, FastMCP):
            key = f"fastmcp_{id(server_conf)}"
        else:
            key = f"{server_conf.type}_{server_conf.name}"

        if key not in self.clients:
            self.clients[key] = self._create_client(server_conf)

        return self.clients[key]

    async def get_tools(self) -> List[BaseTool]:
        """
        Connect to all configured MCP servers, list tools, and convert them to CrewAI BaseTools.
        """
        all_tools = []

        for server_conf in self.servers:
            try:
                # Use cached client context logic?
                # FastMCP/Client are ContextManagers.
                # If we want to keep them open, we need to enter them once and not exit?
                # For safety/simplicity in this fix, we still use context manager but reuse the object.

                # Create a temporary client just for listing (or reuse cached one if feasible)
                # Note: listing tools is rare (startup), so standard context manager is fine here.
                client_context = self._create_client(server_conf)

                # We use the client temporarily to get schema
                async with client_context as client:
                    mcp_tools = await client.list_tools()

                    for tool in mcp_tools:
                        try:
                            # Create Pydantic model for arguments
                            args_schema = _json_schema_to_pydantic(tool.name, tool.inputSchema)

                            # Create the worker function
                            # Capture server_conf in closure
                            async def _tool_func(*args, tool_name=tool.name, _conf=server_conf, **kwargs):
                                # Re-connect for execution logic
                                # Note: Ideally we keep the connection open.
                                # Creating a NEW client object is safe but slow.
                                # Using `nest_asyncio` fixes the crash.

                                # Circuit Breaker / Retry Logic
                                try:
                                    async for attempt in AsyncRetrying(
                                        stop=stop_after_attempt(3),
                                        wait=wait_exponential(multiplier=1, min=2, max=10),
                                        retry=retry_if_exception_type((ConnectionError, TimeoutError, ValueError)),
                                        reraise=True,
                                    ):
                                        with attempt:
                                            async with self._create_client(_conf) as active_client:
                                                app_logger.debug(
                                                    f"DEBUG: Calling tool {tool_name} with args {kwargs} (Attempt {attempt.retry_state.attempt_number})"
                                                )
                                                result = await active_client.call_tool(tool_name, arguments=kwargs)
                                                output = []
                                                if result.content:
                                                    for item in result.content:
                                                        if hasattr(item, "text"):
                                                            output.append(item.text)
                                                return "\n".join(output)
                                except Exception as e:
                                    error_msg = str(e)
                                    if len(error_msg) > 200:
                                        error_msg = error_msg[:200] + "... (error truncated)"

                                    app_logger.error(
                                        f"ERROR: Failed to execute tool {tool_name} after retries: {error_msg}"
                                    )
                                    return f"Error executing tool {tool_name}: {error_msg}"

                            # Sync wrapper with SAFE execution
                            def _sync_tool_func(*args, _target=_tool_func, **kwargs):
                                import concurrent.futures

                                try:
                                    loop = asyncio.get_running_loop()
                                except RuntimeError:
                                    loop = None

                                if loop and loop.is_running():
                                    # We are in a running loop (FastAPI).
                                    # Check if we can use nest_asyncio
                                    loop_type = type(loop).__name__
                                    if "uvloop" in loop_type.lower():
                                        # uvloop doesn't support nest_asyncio
                                        # Run in a new thread with its own event loop
                                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                                            future = executor.submit(asyncio.run, _target(*args, **kwargs))
                                            return future.result()
                                    else:
                                        # Standard loop - use nest_asyncio
                                        _safe_apply_nest_asyncio(loop)
                                        return loop.run_until_complete(_target(*args, **kwargs))
                                else:
                                    return asyncio.run(_target(*args, **kwargs))

                            # Use custom CrewMCPTool
                            crew_tool = CrewMCPTool(
                                sync_tool_func=_sync_tool_func,
                                async_tool_func=_tool_func,
                                name=tool.name,
                                description=tool.description or "",
                                args_schema=args_schema,
                            )
                            all_tools.append(crew_tool)

                        except Exception as e:
                            app_logger.error(f"Error converting tool {tool.name}: {e}")
                            continue

            except Exception as e:
                server_name = getattr(server_conf, "name", "unknown")
                server_url = getattr(server_conf, "url", "unknown") if hasattr(server_conf, "url") else "stdio"

                app_logger.error(f"Failed to load tools from MCP server '{server_name}' ({server_url}). Error: {e}")

                # FAIL FAST: We propagate the error so the Registry knows this agent is broken.
                raise RuntimeError(f"Critical: Could not load tools from server '{server_name}': {e}")

        return all_tools

    def _create_client(self, conf: Union[FastMCP, MCPServerConfig]):
        """
        Helper to return a Client context manager based on config.
        """
        if isinstance(conf, FastMCP):
            return Client(conf)

        # It's an MCPServerConfig
        if conf.type == "stdio":
            return Client(conf.command, args=conf.args, env=conf.env)  # fastmcp. Client supports command+args
        if conf.type == "sse" or conf.type == "https":
            return Client(conf.url, timeout=30)
        else:
            raise ValueError(f"Unknown server type: {conf.type}")

    async def get_server_tools_map(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Connect to all servers and return a map of server_name -> list of tool metadata.
        Used by the Architect to know what tools are available and where.
        """
        server_map = {}

        for server_conf in self.servers:
            try:
                # Use name from config or fallback
                server_name = getattr(server_conf, "name", "unknown")

                # Determine how to connect based on type
                client_context = self._create_client(server_conf)

                async with client_context as client:
                    mcp_tools = await client.list_tools()

                    tool_list = []
                    for tool in mcp_tools:
                        tool_list.append(
                            {"name": tool.name, "description": tool.description or "No description provided."}
                        )

                    server_map[server_name] = tool_list

            except Exception as e:
                app_logger.error(f"Error listing tools for server {getattr(server_conf, 'name', 'unknown')}: {e}")
                server_map[getattr(server_conf, "name", "unknown")] = [{"error": str(e)}]

        return server_map
