import glob
import os
from typing import Any, Dict, List, Optional

import yaml
from crewai import Agent, Task
from pydantic import BaseModel, Field

from src.crew.agents import llm
from src.models.infrastructure import InfrastructureConfig

# -------------------------------------------------------------------------
# Schemas
# -------------------------------------------------------------------------


class AgentConfig(BaseModel):
    role: str
    goal: str
    backstory: str
    verbose: bool = True
    allow_delegation: bool = False
    tools: List[str] = Field(default_factory=list)
    mcp_servers: List[str] = Field(default_factory=list)
    files_access: bool = False
    s3_access: bool = False


class TaskConfig(BaseModel):
    description: str
    expected_output: str
    async_execution: bool = False


class NodeConfig(BaseModel):
    name: str = Field(..., description="Graph Node Name")
    display_name: str = Field(..., description="Supervisor Prompt Name")
    description: str = Field(..., description="Supervisor Prompt Description")
    output_state_key: str = Field("crew_output", description="State key to update with result")
    agent: AgentConfig
    task: TaskConfig


# -------------------------------------------------------------------------
# Registry
# -------------------------------------------------------------------------


class AgentRegistry:
    _instance = None
    _agents: Dict[str, NodeConfig] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentRegistry, cls).__new__(cls)
            cls._instance._load_registry()
        return cls._instance

    def _load_registry(self):
        """Load all YAML files from src/config/agents/"""
        # Determine path relative to this file or project root
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # backend/
        config_path = os.path.join(base_path, "src", "config", "agents", "*.yaml")

        self._agents = {}  # Clear existing
        yaml_files = glob.glob(config_path)
        print(f"Loading agents from {config_path}...")

        for file_path in yaml_files:
            try:
                with open(file_path, "r") as f:
                    data = yaml.safe_load(f)
                    node_config = NodeConfig(**data)
                    self._agents[node_config.name] = node_config
                    print(f"Loaded agent node: {node_config.name}")
            except Exception as e:
                print(f"Error loading agent YAML {file_path}: {e}")

    def reload(self):
        """Reload the registry from disk."""
        self._load_registry()

    def get_all(self) -> List[NodeConfig]:
        return list(self._agents.values())

    def get_config(self, name: str) -> Optional[NodeConfig]:
        return self._agents.get(name)

    async def _fetch_mcp_servers(self, server_names: List[str]) -> List[Any]:
        """Fetch MCP server configurations from the database by name."""
        from src.core.database import pool
        from src.models.mcp import MCPServerConfig

        servers = []
        if not server_names:
            return servers

        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    # Construct query for specific names
                    placeholders = ",".join(["%s"] * len(server_names))
                    query = f"SELECT id, name, type, command, args, url, env FROM mcp_servers WHERE name IN ({placeholders})"
                    await cur.execute(query, tuple(server_names))
                    rows = await cur.fetchall()

                    for row in rows:
                        servers.append(
                            MCPServerConfig(
                                id=row[0],
                                name=row[1],
                                type=row[2],
                                command=row[3],
                                args=row[4] if row[4] else [],
                                url=row[5],
                                env=row[6] if row[6] else {},
                            )
                        )

                    # Also support "default" or local hardcoded if strictly needed,
                    # but for now we assume DB source of truth + potentially the 'mcp' global if "local" is requested and not in DB?
                    # actually, let's stick to DB. If "local" or "fastmcp" was passed and corresponds to a DB entry, good.
        except Exception as e:
            print(f"Error fetching MCP servers: {e}")

        return servers

    async def create_agent(self, name: str, infra: Optional[InfrastructureConfig] = None) -> Optional[Agent]:
        """Instantiate a CrewAI Agent from config."""
        config = self.get_config(name)
        if not config:
            return None

        # Resolve Tools
        agent_tools = []

        # 1. MCP Tools
        if config.agent.mcp_servers:
            from src.tools.adapter import MCPAdapter
            from src.tools.server import mcp

            # Fetch configs from DB
            server_configs = await self._fetch_mcp_servers(config.agent.mcp_servers)

            # Fallback/Hybrid: If "local" or "fastmcp" is requested but not in DB (or if we want to use the running instance)
            # define a special case.
            if "fastmcp" in config.agent.mcp_servers or "local" in config.agent.mcp_servers:
                # Check if we already have it from DB?
                # If not, add the global 'mcp' server instance
                # This allows the 'fastmcp' defined in src.tools.server to be used
                if not any(s.name in ["fastmcp", "local"] for s in server_configs):
                    server_configs.append(mcp)

            if server_configs:
                adapter = MCPAdapter(server_configs)
                mcp_tools = await adapter.get_tools()
                agent_tools.extend(mcp_tools)

        # 2. File Access (Async)
        if config.agent.files_access:
            from src.tools.files import AsyncFileReadTool, AsyncFileWriteTool

            # Determine root_dir from infra if available
            root_dir = infra.local_workspace_path if infra else None

            agent_tools.append(AsyncFileReadTool(root_dir=root_dir))
            agent_tools.append(AsyncFileWriteTool(root_dir=root_dir))

        # 3. S3 Access (Async)
        if config.agent.s3_access:
            from src.tools.s3 import AsyncS3ListBucketsTool, AsyncS3ReadTool, AsyncS3WriteTool

            s3_conf = infra.s3_config if infra else None

            agent_tools.append(AsyncS3ListBucketsTool(s3_config=s3_conf))
            agent_tools.append(AsyncS3ReadTool(s3_config=s3_conf))
            agent_tools.append(AsyncS3WriteTool(s3_config=s3_conf))

        return Agent(
            role=config.agent.role,
            goal=config.agent.goal,
            backstory=config.agent.backstory,
            verbose=config.agent.verbose,
            allow_delegation=config.agent.allow_delegation,
            llm=llm,
            tools=agent_tools,
        )

    def create_task(self, name: str, agent: Agent, inputs: Dict[str, Any] = {}) -> Optional[Task]:
        """Instantiate a CrewAI Task from config, substituting variables in description/goal."""
        config = self.get_config(name)
        if not config:
            return None

        # Simple string formatting for description/goal if they contain {placeholders}
        # Note: CrewAI handles {topic} mostly in goal if passed as inputs?
        # Actually Task.description is where we usually format.

        # We'll do a safe format logic
        description = config.task.description
        try:
            description = description.format(**inputs)
        except KeyError:
            pass  # Keep original if keys missing, or let CrewAI handle it if it supports parsing

        return Task(
            description=description,
            agent=agent,
            expected_output=config.task.expected_output,
            async_execution=config.task.async_execution,
        )
