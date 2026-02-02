from typing import Dict, List, Optional

from crewai.tools import BaseTool

from brain.logger import app_logger
from models.mcp import MCPServerConfig
from services.mcp import mcp_service
from tools.adapter import MCPAdapter


class GlobalToolService:
    _instance = None
    _tools: List[BaseTool] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalToolService, cls).__new__(cls)
        return cls._instance

    async def refresh_tools(self) -> List[BaseTool]:
        """
        Re-scans database locally to load all available tools.
        Refreshes the cache.
        """
        all_configs: List[MCPServerConfig] = []

        # 1. Get DB configurations (Single Source of Truth)
        db_configs = await mcp_service.get_all_servers()
        all_configs.extend(db_configs)

        # 2. Initialize Adapter
        # Note: MCPAdapter handles both MCPServerConfig objects and FastMCP instances
        adapter_targets = all_configs

        adapter = MCPAdapter(adapter_targets)

        try:
            self._tools = await adapter.get_tools()
        except Exception as e:
            app_logger.error(f"Error loading tools: {e}")
            self._tools = []  # Fail safe

        return self._tools

    async def get_all_tools(self, force_refresh: bool = False) -> List[BaseTool]:
        """Get all loaded tools."""
        if not self._tools or force_refresh:
            await self.refresh_tools()
        return self._tools

    async def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Find a specific tool by name."""
        # Check cache first
        tool = next((t for t in self._tools if t.name == tool_name), None)
        if tool:
            return tool

        # Try one refresh if not found (maybe new server added?)
        await self.refresh_tools()
        return next((t for t in self._tools if t.name == tool_name), None)

    async def get_server_tool_map(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Returns a map of server_name -> list of tools {name, description}.
        Used by Architect to know what tools are available.
        """
        all_configs: List[MCPServerConfig] = []

        # 1. Get DB configurations
        db_configs = await mcp_service.get_all_servers()
        all_configs.extend(db_configs)

        # 2. Add local
        adapter_targets = all_configs

        adapter = MCPAdapter(adapter_targets)
        return await adapter.get_server_tools_map()


# Global Instance
tool_service = GlobalToolService()
