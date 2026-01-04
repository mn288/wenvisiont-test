from datetime import UTC, datetime
from typing import List, Optional

from src.brain.registry import AgentRegistry
from src.crew.agents import llm
from src.models.state import AgentResult


class OrchestratorService:
    """
    Handles the 'Brain' logic: Deciding which agent/tool to call next based on state.
    Decoupled from LangGraph nodes to allow easier testing and strict typing.
    """

    def __init__(self):
        self.registry = AgentRegistry()

    async def decide_next_step(
        self, request: str, history: List[AgentResult], context: Optional[str] = ""
    ) -> List[str]:
        """
        Analyzes the current state and returns a list of agent names to execute.
        Returns ["qa"] if the task is complete.
        """

        # 1. Get Available Agents
        registered_nodes = self.registry.get_all()
        dynamic_agent_names = [node.display_name for node in registered_nodes]

        dynamic_agents_desc = "\n    ".join(
            [
                f"{idx + 1}. {node.display_name} ({node.agent.role}): {node.description}\n       Primary Goal: {node.agent.goal}"
                for idx, node in enumerate(registered_nodes)
            ]
        )

        ["QA", "TOOLS"] + dynamic_agent_names

        # 2. Format History
        history_desc = "No history yet."
        if history:
            # We use the strict AgentResult model here
            history_desc = "\n    ".join(
                [
                    f"- [{res.timestamp}] Task {res.task_id} completed. Summary: {res.summary[:300]}..."
                    for res in history
                ]
            )

        current_time = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

        # 3. Construct Prompt
        prompt = f"""You are the Orchestrator of an intelligent agent system.
        Your goal is to coordinate the completion of the user's request by delegating to the most appropriate agent(s) or tool.

        User Request: "{request}"

        Current Context/Findings:
        {context if context else "None"}
        
        Execution History (most recent last):
        {history_desc}

        Current Time: {current_time}

        Available Agents & Tools:
        - QA: Quality Assurance & User Communication. SELECT THIS to finish the task, answer the user, or if you need to ask a clarifying question.
        - TOOLS: MCP Tool Executor. SELECT THIS to run specific tools (e.g., calendar, search, jira) if the request implies taking an action or fetching external data.
        - {", ".join(dynamic_agent_names)}

        Agent Descriptions:
        {dynamic_agents_desc}

        Instructions:
        1. Review the User Request and Execution History.
        2. If the detailed execution history shows an agent has JUST run, avoid re-selecting them immediately unless requested.
        3. If the task is substantially complete, select QA.
        4. You may select MULTIPLE agents if they can work in parallel to save time.
        5. Return a COMMA-SEPARATED list of agent names (e.g. "RESEARCH, ANALYST").

        Return ONLY the comma-separated list of selected agents.
        """

        # 4. LLM Call
        decision_raw = await llm.acall(prompt)
        decisions = [d.strip().upper() for d in decision_raw.split(",")]

        # 5. Validate & Map
        final_next_steps = []

        # Create a normalized map for case-insensitive lookup
        # Map UPPERCASE display name -> actual node name
        node_map = {}
        for node in registered_nodes:
            node_map[node.display_name.upper()] = node.name

        # Add static nodes to map
        node_map["QA"] = "qa"
        node_map["TOOLS"] = "tool_planning"

        for decision in decisions:
            decision_upper = decision.upper().strip()

            if decision_upper in node_map:
                final_next_steps.append(node_map[decision_upper])

        if not final_next_steps:
            final_next_steps = ["qa"]

        return final_next_steps
