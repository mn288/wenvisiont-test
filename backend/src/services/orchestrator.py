from datetime import UTC, datetime
from typing import List, Optional

from brain.registry import AgentRegistry
from crew.agents import llm
from models.state import AgentResult


class OrchestratorService:
    """
    Handles the 'Brain' logic: Deciding which agent/tool to call next based on state.
    Decoupled from LangGraph nodes to allow easier testing and strict typing.
    """

    def __init__(self):
        self.registry = AgentRegistry()

    async def decide_next_step(
        self,
        request: str,
        history: List[AgentResult],
        context: Optional[str] = "",
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[str]:
        """
        Analyzes the current state and returns a list of agent names to execute.
        Returns ["qa"] if the task is complete.
        """

        # 1. Get Available Agents (sorted by DyLAN importance score)
        registered_nodes = sorted(
            self.registry.get_all(),
            key=lambda n: n.agent.importance_score * n.agent.success_rate,
            reverse=True
        )
        dynamic_agent_names = [node.display_name for node in registered_nodes]

        # Include DyLAN scoring info in agent descriptions
        dynamic_agents_desc = "\n    ".join(
            [
                f"{idx + 1}. {node.display_name} ({node.agent.role}) [Score: {node.agent.importance_score:.1f}, Success: {node.agent.success_rate:.0%}]:\n"
                f"       {node.description}\n"
                f"       Domains: {', '.join(node.agent.task_domains) if node.agent.task_domains else 'general'}"
                for idx, node in enumerate(registered_nodes)
            ]
        )


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
        2. **MoA Strategy (Layer 1)**: If the task requires diverse perspectives (e.g., both research and coding), or if DyLAN scores are close, SELECT MULTIPLE agents to run in parallel.
        3. **DyLAN Strategy**: Prioritize agents with higher scores/relevant domains, but allow lower-scored specialized agents if the domain is a perfect match.
        4. If the detailed execution history shows an agent has JUST run, avoid re-selecting them immediately unless requested.
        5. If the task is substantially complete, select QA to synthesize the results (Layer 2 Aggregation).
        6. Return a COMMA-SEPARATED list of agent names (e.g. "RESEARCH, ANALYST").

        Return ONLY the comma-separated list of selected agents.
        """

        # 4. LLM Call
        # Inject Observability
        callbacks = []
        if trace_id:
            from core.observability import get_observability_callback

            callbacks.append(get_observability_callback(trace_id=trace_id, user_id=user_id, trace_name="orchestrator_decision"))

        decision_raw = await llm.acall(prompt, callbacks=callbacks)
        
        # DEBUG: Log logic to file
        try:
            with open("/app/backend/src/debug_orchestrator.log", "a") as f:
                f.write(f"\n--- Decision at {datetime.now(UTC)} ---\n")
                f.write(f"History Count: {len(history)}\n")
                if history:
                    f.write(f"Last Result: {history[-1].summary[:200]}\n")
                f.write(f"LLM Raw Output: {decision_raw}\n")
        except Exception as e:
            print(f"Debug Log Error: {e}")

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
