from typing import Any, Dict

from crewai import Crew, Process, Task

from brain.prompts import DEFAULT_CONTEXT_TEMPLATE, SOP_PROMPT_TEMPLATE, STORAGE_PROTOCOL, THREAD_CONTEXT_TEMPLATE
from brain.registry import AgentRegistry
from models.infrastructure import InfrastructureConfig
from models.state import AgentResult, AgentTask


class CrewService:
    """
    Handles the 'Body' logic: Executing a task using CrewAI agents.

    Architecture: Async Supervisor Swarm
    - LangGraph = Supervisor (state management, routing)
    - CrewAI = Execution Engine (Single-agent Crew wrappers)
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
        # We perform string interpolation here to maintain your custom logic
        task_description = node_config.task.description
        try:
            task_description = task_description.format(
                request=task.input_data,
                research_output=context,
            )
        except KeyError:
            pass

        # Add storage instructions and Context
        task_description = self._inject_storage_instructions(node_config, task_description, thread_id=trace_id)

        if "{research_output}" not in task_description and context:
            task_description += f"\n\nCONTEXT FROM PREVIOUS STEPS:\n{context}"

        if "{request}" not in task_description and task.input_data:
            task_description += f"\n\nORIGINAL REQUEST:\n{task.input_data}"

        # MetaGPT: Inject SOP
        task_description = self._inject_sop(node_config, task_description)

        # 3. Create Agent (passes callbacks to LLM)
        agent_instance = await self.registry.create_agent(agent_name, infra=infra, callbacks=callbacks)

        # 4. Define CrewAI Task (LATEST SYNTAX UPGRADE)
        # CrewAI now requires a Task object with 'expected_output'.
        # We try to get it from config, or fallback to a generic string.
        expected_output = getattr(
            node_config.task, "expected_output", "A detailed response addressing the task description."
        )

        crew_task = Task(description=task_description, expected_output=expected_output, agent=agent_instance)

        # 5. Execute via Crew Wrapper
        # We wrap the single agent in a Crew to ensure robust async tool execution and output parsing.
        crew: Crew = Crew(agents=[agent_instance], tasks=[crew_task], process=Process.sequential, verbose=True)

        try:
            # Native async execution of the crew (v1.7.2+ Syntax)
            result = await crew.akickoff()

            # CrewOutput contains: raw, token_usage, pydantic, json_dict
            result_str = result.raw

            # Handle usage metrics (CrewAI standardizes this in token_usage)
            usage_metrics = getattr(result, "token_usage", {})
            if not usage_metrics and hasattr(result, "usage_metrics"):
                usage_metrics = result.usage_metrics

        except Exception as e:
            raise RuntimeError(f"Agent {agent_name} kickoff failed: {str(e)}") from e

        summary = result_str[:4000] + "..." if len(result_str) > 4000 else result_str

        return AgentResult(
            task_id=task.id,
            summary=summary,
            raw_output=result_str,
            assigned_to=task.assigned_to,
            metadata={
                "agent_role": node_config.agent.role,
                "model": agent_instance.llm.model if hasattr(agent_instance, "llm") else "unknown",
                "usage": self._serialize_usage(usage_metrics),
            },
            timestamp=task.created_at,
        )

    def _inject_storage_instructions(self, node_config, description: str, thread_id: str | None = None) -> str:
        """Inject storage tool instructions into task description using v2.0 Protocol."""

        # Determine context
        if thread_id:
            specific_context = THREAD_CONTEXT_TEMPLATE.format(thread_id=thread_id)
        else:
            specific_context = DEFAULT_CONTEXT_TEMPLATE

        # Build protocol string
        protocol_text = STORAGE_PROTOCOL.format(specific_context=specific_context)

        # Only inject if relevant tools are available
        has_storage = node_config.agent.files_access or node_config.agent.s3_access

        if has_storage and "<data_persistence_protocol>" not in description:
            description += f"\n\n{protocol_text}"

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

    def _inject_sop(self, node_config, description: str) -> str:
        """Inject Standard Operating Procedure using v2.0 XML Tagging."""
        sop = node_config.agent.sop
        if sop:
            return SOP_PROMPT_TEMPLATE.format(sop=sop, description=description)
        return description
