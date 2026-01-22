from typing import Any, Dict

from brain.registry import AgentRegistry
from models.infrastructure import InfrastructureConfig
from models.state import AgentResult, AgentTask


class CrewService:
    """
    Handles the 'Body' logic: Executing a task using CrewAI agents.
    
    Architecture: Async Supervisor Swarm
    - LangGraph = Supervisor (state management, routing)
    - CrewAI = Execution Engine (agent.kickoff_async for native async)
    - FastMCP = Tool Bus (async tool execution)
    """

    def __init__(self):
        self.registry = AgentRegistry()

    async def execute_task(
        self,
        task: AgentTask,
        context: str = "",
        infra: InfrastructureConfig | None = None,
        trace_id: str | None = None,
        user_id: str | None = None,
    ) -> AgentResult:
        """
        Executes a specific task using the assigned agent via native async kickoff.
        
        Uses agent.kickoff_async() - a TRUE async coroutine, not thread-based Future.
        """
        callbacks = []
        if trace_id:
            from core.observability import get_observability_callback

            callbacks.append(
                get_observability_callback(
                    trace_id=trace_id,
                    user_id=user_id,
                    trace_name=f"crew_execution_{task.name}",
                    tags=["crewai", task.name],
                )
            )

        agent_name = task.name

        # 1. Get Configuration
        node_config = self.registry.get_config(agent_name)
        if not node_config:
            raise ValueError(f"Agent {agent_name} not found in registry")

        # 2. Build prompt with context
        task_description = node_config.task.description
        try:
            task_description = task_description.format(
                request=task.input_data,
                research_output=context,
            )
        except KeyError:
            pass  # Keep original if placeholders missing

        # Add storage instructions if applicable
        task_description = self._inject_storage_instructions(node_config, task_description)

        # 3. Create Agent (passes callbacks to LLM)
        agent_instance = await self.registry.create_agent(
            agent_name, infra=infra, callbacks=callbacks
        )

        # 4. Execute via Native Async Kickoff
        # This is the NEW pattern - direct agent interaction without Crew/Task orchestration
        try:
            result = await agent_instance.kickoff_async(
                messages=task_description
            )
            
            # LiteAgentOutput contains: raw, pydantic, agent_role, usage_metrics
            result_str = result.raw if hasattr(result, "raw") else str(result)
            usage_metrics = getattr(result, "usage_metrics", {})
            
        except Exception as e:
            raise RuntimeError(f"Agent {agent_name} kickoff failed: {str(e)}") from e

        summary = result_str[:500] + "..." if len(result_str) > 500 else result_str

        return AgentResult(
            task_id=task.id,
            summary=summary,
            raw_output=result_str,
            metadata={
                "agent_role": node_config.agent.role,
                "model": agent_instance.llm.model if hasattr(agent_instance, "llm") else "unknown",
                "usage": self._serialize_usage(usage_metrics),
            },
            timestamp=task.created_at,
        )

    def _inject_storage_instructions(self, node_config, description: str) -> str:
        """Inject storage tool instructions into task description."""
        storage_instructions = []
        
        if node_config.agent.files_access:
            storage_instructions.append(
                "- To save files locally, use 'AsyncFileWriteTool'. Do not print code; write it to a file."
            )
        if node_config.agent.s3_access:
            storage_instructions.append(
                "- To save files to S3, use 'AsyncS3WriteTool'.\n"
                "- To read files from S3, use 'AsyncS3ReadTool'."
            )

        if storage_instructions and "CRITICAL STORAGE INSTRUCTIONS" not in description:
            header = "\n\nCRITICAL STORAGE INSTRUCTIONS:\n"
            description += header + "\n".join(storage_instructions)

        return description

    def _serialize_usage(self, usage: Any) -> Dict:
        """Safely serialize usage metrics."""
        if hasattr(usage, "model_dump"):
            return usage.model_dump()
        elif hasattr(usage, "dict"):
            return usage.dict()
        elif isinstance(usage, dict):
            return usage
        return {}
