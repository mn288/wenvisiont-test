from typing import Any, Dict, List, Optional
from uuid import uuid4

from crewai import Agent, Task
from pydantic import BaseModel, Field

from core.database import pool
from crew.agents import get_llm, llm
from models.infrastructure import InfrastructureConfig

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
    # CrewAI 2025 parameters
    max_iter: int = 1
    max_retry_limit: int = 1
    max_execution_time: Optional[int] = 30
    respect_context_window: bool = True
    inject_date: bool = True
    # DyLAN-style dynamic agent selection (arXiv:2310.02170)
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Agent importance weight for routing")
    task_domains: List[str] = Field(default_factory=list, description="Domain keywords e.g. ['code', 'research', 'analysis']")
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="Historical task success rate")
    use_reflection: bool = Field(default=False, description="Enable self-correction/reflection step")
    # MetaGPT-style SOP (arXiv:2308.00352)
    sop: Optional[str] = Field(default=None, description="Standard Operating Procedure the agent must follow")


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
# Registry (DB Backed)
# -------------------------------------------------------------------------


class AgentRegistry:
    _instance = None
    _agents: Dict[str, NodeConfig] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentRegistry, cls).__new__(cls)
            # Cannot async load here. Must be called explicitly on startup.
        return cls._instance

    async def load_agents(self):
        """Load all agents from the database into the cache."""
        print("Loading agents from Database...")
        self._agents = {}
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT name, config FROM superagents")
                    rows = await cur.fetchall()
                    for row in rows:
                        name, config_data = row
                        try:
                            # Config is stored as JSON dict in DB
                            node_config = NodeConfig(**config_data)
                            self._agents[node_config.name] = node_config
                            print(f"Loaded agent node: {node_config.name}")
                        except Exception as e:
                            print(f"Error parsing agent {name}: {e}")
        except Exception as e:
            print(f"Error loading agents from DB: {e}")

    async def save_agent(self, config: NodeConfig):
        """Save or update an agent in the database and cache."""
        # Update Cache
        self._agents[config.name] = config

        # Persist to DB
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # Upsert logic (Postgres 9.5+)
                # We store the Pydantic dump as JSON
                config_json = config.model_dump_json()  # Use json string for SQL param

                await cur.execute(
                    """
                    INSERT INTO superagents (id, name, config, created_at, updated_at)
                    VALUES (%s, %s, %s::jsonb, NOW(), NOW())
                    ON CONFLICT (name) 
                    DO UPDATE SET config = EXCLUDED.config, updated_at = NOW()
                    """,
                    (uuid4(), config.name, config_json),
                )
            await conn.commit()

    async def delete_agent(self, name: str):
        """Delete an agent from the database and cache."""
        if name in self._agents:
            del self._agents[name]

        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM superagents WHERE name = %s", (name,))
            await conn.commit()

    async def update_agent_success_rate(self, name: str, success: bool, alpha: float = 0.1):
        """
        Update agent success_rate using exponential moving average (DyLAN feedback loop).
        
        Args:
            name: Agent name
            success: Whether the task succeeded
            alpha: Learning rate (0.1 = slow adaptation, 0.5 = fast adaptation)
        """
        config = self.get_config(name)
        if not config:
            return
        
        # Exponential moving average: new_rate = alpha * outcome + (1 - alpha) * old_rate
        outcome = 1.0 if success else 0.0
        new_rate = alpha * outcome + (1 - alpha) * config.agent.success_rate
        config.agent.success_rate = round(new_rate, 2)
        
        # Persist updated config
        await self.save_agent(config)

    def reload(self):
        """
        Reload the registry.
        WARNING: This is now async incompatible if called synchronously.
        Ideally should be await reload().
        For legacy compatibility, we might need a workaround or ensure callers await.
        """
        pass  # Deprecated sync reload. Use load_agents()

    def get_all(self) -> List[NodeConfig]:
        return list(self._agents.values())

    def get_config(self, name: str) -> Optional[NodeConfig]:
        """Get agent configuration by name."""
        return self._agents.get(name)

    async def _fetch_mcp_servers(self, server_names: List[str]) -> List[Any]:
        """Fetch MCP server configurations from the database by name."""
        from models.mcp import MCPServerConfig

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
        except Exception as e:
            print(f"Error fetching MCP servers: {e}")

        return servers

    def validate_node_names(self, node_names: List[str]) -> List[str]:
        """
        Validate that a list of node names exists in the registry.
        Returns a list of invalid names.
        """
        return [name for name in node_names if name not in self._agents]

    async def create_agent(
        self,
        name: str,
        infra: Optional[InfrastructureConfig] = None,
        callbacks: List[Any] | None = None,
    ) -> Optional[Agent]:
        """Instantiate a CrewAI Agent from config."""
        config = self.get_config(name)
        if not config:
            return None

        # Resolve Tools
        agent_tools = []

        # 1. MCP Tools
        if config.agent.mcp_servers:
            from tools.adapter import MCPAdapter
            from tools.server import mcp

            # Fetch configs from DB
            server_configs = await self._fetch_mcp_servers(config.agent.mcp_servers)

            # Fallback/Hybrid: If "local" or "fastmcp" is requested but not in DB
            if "fastmcp" in config.agent.mcp_servers or "local" in config.agent.mcp_servers:
                if not any(s.name in ["fastmcp", "local"] for s in server_configs):
                    server_configs.append(mcp)

            if server_configs:
                adapter = MCPAdapter(server_configs)
                mcp_tools = await adapter.get_tools()
                agent_tools.extend(mcp_tools)

        # 2. File Access (Async)
        if config.agent.files_access:
            from tools.files import AsyncFileReadTool, AsyncFileWriteTool

            # Determine root_dir from infra if available
            root_dir = infra.local_workspace_path if infra else None

            agent_tools.append(AsyncFileReadTool(root_dir=root_dir))
            agent_tools.append(AsyncFileWriteTool(root_dir=root_dir))
        # 3. S3 Access (Async)
        if config.agent.s3_access:
            from tools.s3 import AsyncS3ListBucketsTool, AsyncS3ReadTool, AsyncS3WriteTool

            s3_conf = infra.s3_config if infra else None

            agent_tools.append(AsyncS3ListBucketsTool(s3_config=s3_conf))
            agent_tools.append(AsyncS3ReadTool(s3_config=s3_conf))
            agent_tools.append(AsyncS3WriteTool(s3_config=s3_conf))
        print(f"DEBUG: Creating agent {name} with tools: {[t.name for t in agent_tools]}")

        # Instantiate LLM with callbacks if provided
        agent_llm = get_llm(callbacks) if callbacks else llm

        return Agent(
            role=config.agent.role,
            goal=config.agent.goal,
            backstory=config.agent.backstory,
            verbose=config.agent.verbose,
            allow_delegation=False,  # CRITICAL: Force False to prevent competing orchestration
            llm=agent_llm,
            tools=agent_tools,
            # New CrewAI 2025 parameters
            max_iter=config.agent.max_iter,
            max_retry_limit=config.agent.max_retry_limit,
            max_execution_time=config.agent.max_execution_time,
            respect_context_window=config.agent.respect_context_window,
            inject_date=config.agent.inject_date,
        )

    def create_task(self, name: str, agent: Agent, inputs: Dict[str, Any] = {}) -> Optional[Task]:
        """Instantiate a CrewAI Task from config, substituting variables in description/goal."""
        config = self.get_config(name)
        if not config:
            return None

        description = config.task.description
        # Enforce Storage Instructions
        storage_instructions = []
        if config.agent.files_access:
            storage_instructions.append(
                "- To save files locally, you MUST use the 'AsyncFileWriteTool'. Do not print code/content; write it to a file."
            )
        if config.agent.s3_access:
            storage_instructions.append(
                "- To save files to S3, you MUST use the 'AsyncS3WriteTool'.\n- To read files from S3, you MUST use the 'AsyncS3ReadTool'.\n- To list S3 buckets, you MUST use the 'AsyncS3ListBucketsTool'.\n- To delete files from S3, you MUST use the 'AsyncS3DeleteObjectTool'.\n- To update files in S3, you MUST use the 'AsyncS3UpdateObjectTool'."
            )

        if storage_instructions:
            header = "\n\nCRITICAL STORAGE INSTRUCTIONS:\n"
            full_instruction = header + "\n".join(storage_instructions)

            # Avoid duplication if already present (simple check)
            if "CRITICAL STORAGE INSTRUCTIONS" not in description:
                description += full_instruction

        try:
            description = description.format(**inputs)
        except KeyError:
            pass

        return Task(
            description=description,
            agent=agent,
            expected_output=config.task.expected_output,
            async_execution=config.task.async_execution,
        )
