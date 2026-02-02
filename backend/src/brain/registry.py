from typing import Any, Dict, List, Optional
from uuid import uuid4

# CrewAI Imports
from crewai import Agent, Task

from brain.logger import app_logger
from brain.prompts import (
    DEFAULT_CONTEXT_TEMPLATE,
    DYNAMIC_AGENT_BACKSTORY,
    DYNAMIC_AGENT_GOAL,
    DYNAMIC_AGENT_ROLE,
    DYNAMIC_AGENT_TASK,
    STORAGE_PROTOCOL,
)
from core.database import pool
from crew.agents import get_llm, llm

# -------------------------------------------------------------------------
# Schemas
# -------------------------------------------------------------------------
from models.agents import AgentConfig, NodeConfig, TaskConfig
from models.infrastructure import InfrastructureConfig

# -------------------------------------------------------------------------
# Registry (DB Backed)
# -------------------------------------------------------------------------


class AgentRegistry:
    _instance = None
    _agents: Dict[str, NodeConfig] = {}
    _workflows: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentRegistry, cls).__new__(cls)
        return cls._instance

    async def load_agents(self):
        """Load all agents from the database into the cache."""
        app_logger.info("Loading agents from Database...")
        self._agents = {}
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT name, config FROM superagents")
                    rows = await cur.fetchall()
                    for row in rows:
                        name, config_data = row
                        try:
                            node_config = NodeConfig(**config_data)
                            self._agents[node_config.name] = node_config
                            app_logger.info(f"Loaded agent node: {node_config.name}")
                        except Exception as e:
                            app_logger.error(f"Error parsing agent {name}: {e}")
        except Exception as e:
            app_logger.error(f"Error loading agents from DB: {e}")

        # ---------------------------------------------------------
        # Dynamic Loading: MCP Servers as Standalone Agents
        # ---------------------------------------------------------
        try:
            app_logger.info("Loading dynamic MCP agents...")
            from services.mcp import mcp_service

            servers = await mcp_service.get_all_servers()

            for server in servers:
                safe_name = server.name.lower().replace(" ", "_").replace("-", "_")
                agent_name = f"mcp_agent_{safe_name}"

                if agent_name in self._agents:
                    app_logger.info(f"Skipping dynamic agent {agent_name} (Shadowed by DB agent)")
                    continue

                # Construct Dynamic Config via Adapter
                from tools.adapter import MCPAdapter

                tool_summary = "No specific tools listed."
                try:
                    adapter = MCPAdapter([server])
                    tools = await adapter.get_tools()

                    if tools:
                        tool_desc_list = [f"- {t.name}: {t.description}" for t in tools]
                        tool_summary = "\n".join(tool_desc_list)
                    else:
                        app_logger.warning(f"Warning: Server {server.name} returned 0 tools. Skipping agent creation.")
                        continue

                except Exception as tool_err:
                    app_logger.error(f"Removing '{agent_name}' from registry because tool loading failed: {tool_err}")
                    continue

                # 1. Agent Config
                agent_config = AgentConfig(
                    role=DYNAMIC_AGENT_ROLE.format(server_name=server.name),
                    goal=DYNAMIC_AGENT_GOAL.format(server_name=server.name),
                    backstory=DYNAMIC_AGENT_BACKSTORY.format(server_name=server.name, tool_summary=tool_summary),
                    mcp_servers=[server.name],
                    files_access=True,
                    use_reflection=True,
                    task_domains=["tools", server.name.lower(), "execution"],
                    importance_score=0.5,
                    success_rate=1.0,
                    max_iter=15,
                )

                # 2. Task Configuration
                task_config = TaskConfig(
                    description=DYNAMIC_AGENT_TASK.format(request="{request}"),
                    expected_output="Result of the tool execution.",
                    async_execution=False,
                )

                # 3. Node Configuration
                node_config = NodeConfig(
                    name=agent_name,
                    display_name=f"ToolAgent_{server.name}",
                    description=f"Agent with access to '{server.name}' tools.\nCapabilities:\n{tool_summary}",
                    agent=agent_config,
                    task=task_config,
                )

                self._agents[agent_name] = node_config
                app_logger.info(f"Loaded dynamic MCP agent: {agent_name} ({node_config.display_name})")

        except Exception as e:
            app_logger.error(f"Error loading dynamic MCP agents: {e}")

        await self.load_workflows()

    async def load_workflows(self):
        """Load all workflows from the database into the cache."""
        from models.architect import GraphConfig

        app_logger.info("Loading workflows from Database...")
        self._workflows = {}
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT name, config FROM workflows")
                    rows = await cur.fetchall()
                    for row in rows:
                        name, config_data = row
                        try:
                            workflow_config = GraphConfig(**config_data)
                            self._workflows[workflow_config.name] = workflow_config
                            app_logger.info(f"Loaded workflow: {workflow_config.name}")

                            if workflow_config.definitions:
                                for agent_def in workflow_config.definitions:
                                    self._agents[agent_def.name] = agent_def
                                    app_logger.info(f"Loaded workflow-defined agent: {agent_def.name}")

                        except Exception as e:
                            app_logger.error(f"Error parsing workflow {name}: {e}")
        except Exception as e:
            app_logger.error(f"Error loading workflows from DB: {e}")

    async def save_agent(self, config: NodeConfig):
        """Save or update an agent in the database and cache."""
        self._agents[config.name] = config
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                config_json = config.model_dump_json()
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

    async def save_workflow(self, config: Any):
        """Save or update a workflow in the database and cache."""
        self._workflows[config.name] = config

        if config.definitions:
            for agent_def in config.definitions:
                self._agents[agent_def.name] = agent_def

        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                config_json = config.model_dump_json()
                await cur.execute(
                    """
                    INSERT INTO workflows (id, name, config, created_at, updated_at)
                    VALUES (%s, %s, %s::jsonb, NOW(), NOW())
                    ON CONFLICT (name) 
                    DO UPDATE SET config = EXCLUDED.config, updated_at = NOW()
                    """,
                    (uuid4(), config.name, config_json),
                )
            await conn.commit()

    async def delete_agent(self, name: str):
        if name in self._agents:
            del self._agents[name]
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM superagents WHERE name = %s", (name,))
            await conn.commit()

    async def delete_workflow(self, name: str):
        if name in self._workflows:
            workflow = self._workflows[name]
            if workflow.definitions:
                for agent_def in workflow.definitions:
                    await self.delete_agent(agent_def.name)
            del self._workflows[name]

        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM workflows WHERE name = %s", (name,))
            await conn.commit()

    async def update_agent_success_rate(self, name: str, success: bool, alpha: float = 0.1):
        config = self.get_config(name)
        if not config:
            return
        outcome = 1.0 if success else 0.0
        new_rate = alpha * outcome + (1 - alpha) * config.agent.success_rate
        config.agent.success_rate = round(new_rate, 2)
        await self.save_agent(config)

    def reload(self):
        pass

    def get_all(self) -> List[NodeConfig]:
        return list(self._agents.values())

    def get_config(self, name: str) -> Optional[NodeConfig]:
        return self._agents.get(name)

    async def _fetch_mcp_servers(self, server_names: List[str]) -> List[Any]:
        from services.mcp import mcp_service

        return await mcp_service.get_servers_by_names(server_names)

    def get_workflows(self) -> List[Any]:
        return list(self._workflows.values())

    def validate_node_names(self, node_names: List[str]) -> List[str]:
        workflow_names = [w.name for w in self.get_workflows()]
        valid_names = list(self._agents.keys()) + workflow_names
        return [name for name in node_names if name not in valid_names]

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

        # 2. File Access (Via MCP)
        if config.agent.files_access:
            app_logger.debug(f"DEBUG: Agent {name} requires file access. Ensuring 'filesystem' MCP is loaded.")
            if "filesystem" not in config.agent.mcp_servers:
                config.agent.mcp_servers.append("filesystem")

        # 3. S3 Access (Via MCP)
        if config.agent.s3_access:
            app_logger.debug(f"DEBUG: Agent {name} requires S3 access. Ensuring 's3' MCP is loaded.")
            if "s3" not in config.agent.mcp_servers:
                config.agent.mcp_servers.append("s3")

        # Reload tools with new server list if needed
        # (This implies a re-fetch if we modified the list... but simplest is to just fetch after modifying)

        # ---------------------------------------------------------
        # MCP TOOL LOADING (Consolidated)
        # ---------------------------------------------------------
        if config.agent.mcp_servers:
            from tools.adapter import MCPAdapter

            server_configs = await self._fetch_mcp_servers(config.agent.mcp_servers)

            if server_configs:
                try:
                    adapter = MCPAdapter(server_configs)
                    mcp_tools = await adapter.get_tools()
                    agent_tools.extend(mcp_tools)
                except Exception as e:
                    app_logger.critical(f"CRITICAL: Failed to load tools for agent {name} at runtime: {e}")
                    # Do not raise hard error, allow agent to start without broken tools (or decide policy)
                    # raise RuntimeError(f"Agent {name} failed initialization: MCP Connection Error: {e}")
                    app_logger.warning("Continuing without some tools...")

            if config.agent.mcp_servers and not mcp_tools and not agent_tools:
                app_logger.warning(
                    f"WARNING: Agent {name} requested MCP servers {config.agent.mcp_servers} but no tools were loaded."
                )

        app_logger.debug(f"DEBUG: Creating agent {name} with tools: {[t.name for t in agent_tools]}")

        # Instantiate LLM with callbacks if provided
        agent_llm = get_llm(callbacks) if callbacks else llm

        return Agent(
            role=config.agent.role,
            goal=config.agent.goal,
            backstory=config.agent.backstory,
            verbose=config.agent.verbose,
            # allow_delegation=False,  <-- REMOVED: Deprecated/Noisy in recent versions.
            llm=agent_llm,
            tools=agent_tools,
            # callbacks=callbacks,  # REMOVED: Agent callbacks must be callables, not LangChain objects. LLM handles observability.
            # CrewAI Limits
            max_iter=config.agent.max_iter,
            max_retry_limit=config.agent.max_retry_limit,
            max_execution_time=config.agent.max_execution_time,
            respect_context_window=config.agent.respect_context_window,
            # inject_date=config.agent.inject_date, # Optional based on your config schema
        )

    def create_task(self, name: str, agent: Agent, inputs: Dict[str, Any] = {}) -> Optional[Task]:
        """Instantiate a CrewAI Task from config, substituting variables in description/goal."""
        config = self.get_config(name)
        if not config:
            return None

        description = config.task.description

        # Enforce Storage Instructions (v2.0 Protocol)
        # Note: registry.create_task handles instantiation, likely without specific thread_id context yet.
        # We use DEFAULT_CONTEXT_TEMPLATE.
        if config.agent.files_access or config.agent.s3_access:
            if "<data_persistence_protocol>" not in description:
                protocol_text = STORAGE_PROTOCOL.format(specific_context=DEFAULT_CONTEXT_TEMPLATE)
                description += f"\n\n{protocol_text}"

        try:
            description = description.format(**inputs)
        except KeyError:
            pass

        # Handle fallback for expected_output (Required in new CrewAI)
        expected_output = config.task.expected_output
        if not expected_output:
            expected_output = "A detailed result based on the task description."

        return Task(
            description=description,
            agent=agent,
            expected_output=expected_output,
            async_execution=config.task.async_execution,
        )
