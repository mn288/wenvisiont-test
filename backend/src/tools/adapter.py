import asyncio
from typing import Any, Callable, Dict, List, Optional, Type, Union

from crewai.tools import BaseTool
from fastmcp import Client, FastMCP
from pydantic import BaseModel, PrivateAttr, create_model

# Check if MCPServerConfig is available, if not use Dict or define locally for typing
try:
    from models.mcp import MCPServerConfig
except ImportError:
    MCPServerConfig = Any


def _json_schema_to_pydantic(name: str, schema: Dict[str, Any]) -> Type[BaseModel]:
    """
    Convert a JSON schema to a Pydantic model dynamically.
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
        CRITICAL: This architecture is STRICT ASYNC. Sync execution is forbidden to prevent blocking the event loop.
        """
        raise NotImplementedError("This tool is async-only. Use _arun to prevent blocking the event loop.")

    async def _arun(self, *args, **kwargs):
        """Execute the tool asynchronously."""
        return await self._async_tool_func(*args, **kwargs)


class MCPAdapter:
    def __init__(self, servers: List[Union[FastMCP, MCPServerConfig]]):
        """
        Initialize with a list of servers.
        Items can be:
        - FastMCP instance (for local/in-memory)
        - MCPServerConfig (for external stdio/sse)
        """
        self.servers = servers

    async def get_tools(self) -> List[BaseTool]:
        """
        Connect to all configured MCP servers, list tools, and convert them to CrewAI BaseTools.
        """
        all_tools = []

        for server_conf in self.servers:
            try:
                # Determine how to connect based on type
                client_context = self._get_client(server_conf)

                # We use the client temporarily to get schema
                async with client_context as client:
                    mcp_tools = await client.list_tools()

                    for tool in mcp_tools:
                        # Create Pydantic model for arguments
                        args_schema = _json_schema_to_pydantic(tool.name, tool.inputSchema)

                        # Create the worker function
                        # Capture server_conf in closure
                        async def _tool_func(*args, tool_name=tool.name, _conf=server_conf, **kwargs):
                            # Re-connect for execution
                            # Optimization: Creating a new client/process for every call might be slow for stdio.
                            # Ideally we should keep clients alive, but for simplicity/robustness we restart.
                            async with self._get_client(_conf) as active_client:
                                result = await active_client.call_tool(tool_name, arguments=kwargs)
                                output = []
                                if result.content:
                                    for item in result.content:
                                        if hasattr(item, "text"):
                                            output.append(item.text)
                                return "\n".join(output)

                        # Sync wrapper
                        def _sync_tool_func(*args, **kwargs):
                            return asyncio.run(_tool_func(*args, **kwargs))

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
                import traceback

                print(f"DEBUG: Error loading tools from server {server_conf}: {e}")
                traceback.print_exc()

        return all_tools

    def _get_client(self, conf: Union[FastMCP, MCPServerConfig]):
        """
        Helper to return a Client context manager based on config.
        """
        if isinstance(conf, FastMCP):
            return Client(conf)

        # It's an MCPServerConfig
        if conf.type == "stdio":
            return Client(conf.command, args=conf.args, env=conf.env)  # fastmcp.Client supports command+args
        elif conf.type == "sse" or conf.type == "https":
            return Client(conf.url)
        else:
            raise ValueError(f"Unknown server type: {conf.type}")
