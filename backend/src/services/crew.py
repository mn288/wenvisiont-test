from crewai import Crew

from brain.registry import AgentRegistry
from models.infrastructure import InfrastructureConfig
from models.state import AgentResult, AgentTask


class CrewService:
    """
    Handles the 'Body' logic: Executing a task using CrewAI agents.
    """

    def __init__(self):
        self.registry = AgentRegistry()

    async def execute_task(
        self, task: AgentTask, context: str = "", infra: InfrastructureConfig | None = None
    ) -> AgentResult:
        """
        Executes a specific task using the assigned agent.
        """
        agent_name = task.name

        # 1. Get Configuration
        node_config = self.registry.get_config(agent_name)
        if not node_config:
            raise ValueError(f"Agent {agent_name} not found in registry")

        # 2. Prepare Inputs
        inputs = {
            "request": task.input_data,
            "research_output": context,
        }

        # 3. Create Crew
        agent_instance = await self.registry.create_agent(agent_name, infra=infra)
        task_instance = self.registry.create_task(agent_name, agent_instance, inputs)

        crew = Crew(
            agents=[agent_instance],
            tasks=[task_instance],
            verbose=True,
        )

        # 4. Execute
        result_raw = await crew.akickoff()
        result_str = str(result_raw)

        summary = result_str[:500] + "..." if len(result_str) > 500 else result_str
        token_usage = getattr(result_raw, "token_usage", {})

        return AgentResult(
            task_id=task.id,
            summary=summary,
            raw_output=result_str,
            metadata={
                "agent_role": node_config.agent.role,
                "model": agent_instance.llm.model if hasattr(agent_instance, "llm") else "unknown",
                "usage": token_usage.model_dump()
                if hasattr(token_usage, "model_dump")
                else (token_usage.dict() if hasattr(token_usage, "dict") else token_usage),
            },
        )
