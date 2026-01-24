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
        
        # Get Workflows (Superagent Teams)
        workflows = self.registry.get_workflows()

        dynamic_agent_names = [node.display_name for node in registered_nodes]
        # Add workflow names
        dynamic_agent_names.extend([f"TEAM_{w.name.upper()}" for w in workflows])

        # Include DyLAN scoring info in agent descriptions
        agents_desc = "\n    ".join(
            [
                f"{idx + 1}. {node.display_name} ({node.agent.role}) [Score: {node.agent.importance_score:.1f}, Success: {node.agent.success_rate:.0%}]:\n"
                f"       {node.description}\n"
                f"       Domains: {', '.join(node.agent.task_domains) if node.agent.task_domains else 'general'}"
                for idx, node in enumerate(registered_nodes)
            ]
        )
        
        # Add Workflow descriptions
        workflows_desc = "\n    ".join(
            [
                f"TEAM_{w.name.upper()} (Superagent Team): {w.description}\n       Contains {len(w.nodes)} specialized agents."
                for w in workflows
            ]
        )
        
        dynamic_agents_desc = f"{agents_desc}\n\n    SUPERAGENT TEAMS:\n    {workflows_desc}" if workflows else agents_desc


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
        1. **Analyze the Request**: Identify the specific *domains* (e.g., Code, Research, QA) required. matches against Agent Descriptions.
        2. **Identify Complementary Roles**: Look for agents that form logical pairs for the task:
           - **Creator & Verifier**: (e.g. Coder + QA, Writer + Editor). One produces, the other checks.
           - **Planner & Executor**: One designs the plan, the other carries it out.
           - **Diverse Perspectives**: Multiple agents with different specializations (e.g. Legal + Technical) to address complex queries.
        3. **Explicit Mentions**: If the user explicitly names an agent or role (e.g. "@Coder", "the researcher"), YOU MUST SELECT THEM.
        4. **MoA Strategy (Layer 1)**: 
           - **Parallel Execution**: If the task involves sub-tasks that can be handled by different experts, SELECT ALL RELEVANT AGENTS to run in parallel.
           - **Avoid Bottlenecks**: Do not assign a complex multi-domain task to a single generic agent if specialized agents are available.
        5. **DyLAN Strategy**: Use importance scores as a tie-breaker, but NEVER ignore a better-suited specialized agent (even with a lower score) if they are the best fit for a specific sub-task.
        6. **Context Check**: If the history shows an agent has just run, verify if their output needs downstream processing by a *different* agent.
        7. **Termination**: If the task is fully complete and the user's last question is answered, select "QA" to finalize.

        Return ONLY the comma-separated list of selected agents (e.g. "RESEARCH_AGENT, WRITER_AGENT").
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
            
        # Map Workflows
        for w in workflows:
            node_map[f"TEAM_{w.name.upper()}"] = w.name

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
