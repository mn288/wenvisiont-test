from datetime import UTC, datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from brain.prompts import ORCHESTRATOR_PROMPT
from brain.registry import AgentRegistry
from crew.agents import llm


class OrchestratorDecision(BaseModel):
    """Structured decision output from the Orchestrator."""

    thought_process: str = Field(
        ..., description="Brief analysis of why specific agents are needed based on history and request."
    )
    reasoning: str = Field(..., description="Agent assignment justification.")
    selected_agents: List[str] = Field(
        ...,
        description="List of EXACT agent display names (from Available Assets) to execute. Example: ['ToolAgent_filesystem']. Do NOT include instructions or sentences. If task is complete, use ['QA'].",
    )
    plan: List[str] = Field(
        default_factory=list,
        description="The updated list of FUTURE steps remaining (excluding the one selected now). Example: ['ToolAgent_filesystem']. If task is complete, return [].",
    )


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
        global_state: dict,
        long_term_summary: str,
        conversation_buffer: List[str],
        current_plan: List[str],  # Injected Plan
        last_agent_name: Optional[str] = None,
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        allowed_node_names: Optional[List[str]] = None,
    ) -> tuple[List[str], List[str]]:
        """
        Analyzes the current state and returns (next_step, new_plan).
        Returns ["qa"] if the task is complete.

        Args:
            allowed_node_names: If provided, RESTRICt selection to these nodes only (plus QA/Tools).
        """

        # 1. Get Available Agents (sorted by DyLAN importance score)
        all_nodes = self.registry.get_all()

        # Filter if constraint provided
        if allowed_node_names is not None:
            # We must map 'display_name' or 'name'?
            # The registry uses 'name' (snake_case).
            registered_nodes = [
                n for n in all_nodes if n.name in allowed_node_names or n.display_name in allowed_node_names
            ]
        else:
            registered_nodes = all_nodes

        registered_nodes = sorted(
            registered_nodes, key=lambda n: n.agent.importance_score * n.agent.success_rate, reverse=True
        )

        # Get Workflows (Superagent Teams)
        all_workflows = self.registry.get_workflows()

        # Filter workflows
        if allowed_node_names is not None:
            workflows = [w for w in all_workflows if w.name in allowed_node_names]
        else:
            workflows = all_workflows

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

        dynamic_agents_desc = (
            f"{agents_desc}\n\n    SUPERAGENT TEAMS:\n    {workflows_desc}" if workflows else agents_desc
        )

        if not dynamic_agent_names and not workflows:
            # Fallback if filter excluded everything (shouldn't happen in valid graph)
            dynamic_agents_desc = "No specific agents available."

        # 2. Format Context & History
        import orjson

        # orjson returns bytes, so we decode to str. OPT_INDENT_2 makes it readable for LLM.
        # orjson handles datetime automatically.
        # Helper: Summarize Global State to save tokens
        # We only want to show the LLM *what* is available, not the full content of every artifact.
        def summarize_state(state_data: dict) -> dict:
            summary = {}
            for k, v in state_data.items():
                # If it's a metadata key, keep it
                if k.startswith("_meta"):
                    summary[k] = v
                    continue

                # If it's a large text blob, summarize it
                if isinstance(v, str) and len(v) > 500:
                    summary[k] = f"<Content Truncated: {len(v)} chars>"
                elif isinstance(v, dict):
                    # Recursive summary for nested dicts (limit depth if needed, but simple recursion is fine for now)
                    summary[k] = summarize_state(v)
                elif isinstance(v, list):
                    summary[k] = f"<List of {len(v)} items>"
                else:
                    summary[k] = v
            return summary

        summary_state = summarize_state(global_state)

        # orjson returns bytes, so we decode to str. OPT_INDENT_2 makes it readable for LLM.
        state_json = orjson.dumps(summary_state, option=orjson.OPT_INDENT_2 | orjson.OPT_SERIALIZE_NUMPY).decode(
            "utf-8"
        )

        history_display = "No history yet."
        if conversation_buffer:
            history_display = "\n".join(conversation_buffer)

        current_time = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

        # 3. Construct Prompt
        # Determine status message for last agent if applicable
        last_agent_status_msg = "UNKNOWN"
        if last_agent_name:
            # Basic heuristic: If we are back here, it implies loop or continue.
            # Ideally we check state['results'] but simplified here:
            last_agent_status_msg = "EXECUTED (Check History)"

        prompt = ORCHESTRATOR_PROMPT.format(
            request=request,
            current_time=current_time,
            state_json=state_json,
            long_term_summary=long_term_summary if long_term_summary else "No summary yet.",
            history_display=history_display,
            dynamic_agents_desc=dynamic_agents_desc,
            last_agent_name=last_agent_name if last_agent_name else "NONE",
            last_agent_status_msg=last_agent_status_msg,
            current_plan=str(current_plan) if current_plan else "No plan yet",
        )

        # 4. LLM Call with Structured Output
        callbacks = []
        if trace_id:
            from core.observability import get_observability_callback

            callbacks.append(
                get_observability_callback(trace_id=trace_id, user_id=user_id, trace_name="orchestrator_decision")
            )

        # Configure run config
        run_config = {"callbacks": callbacks} if callbacks else {}

        try:
            # Use the raw client if available to support with_structured_output
            if hasattr(llm, "client"):
                structured_llm = llm.client.with_structured_output(OrchestratorDecision)
                decision: OrchestratorDecision = await structured_llm.ainvoke(prompt, config=run_config)
            else:
                # Fallback if llm wrapper doesn't expose client (should not happen based on inspection)
                print("Warning: llm.client not found, using legacy parsing.")
                # ... legacy code or error ...
                raise NotImplementedError("Orchestrator requires an LLM client supporting structured output.")

        except Exception as e:
            print(f"Orchestrator Structured Output Error: {e}")
            # Fallback to QA if orchestration fails
            return ["qa"], []

        # DEBUG: Log logic to file
        try:
            with open("/app/backend/src/debug_orchestrator.log", "a") as f:
                f.write(f"\n--- Decision at {datetime.now(UTC)} ---\n")
                f.write(f"Thought Process: {decision.thought_process}\n")
                f.write(f"Reasoning: {decision.reasoning}\n")
                f.write(f"Decisions: {decision.selected_agents}\n")
        except Exception as e:
            print(f"Debug Log Error: {e}")

        decisions = [d.strip().upper() for d in decision.selected_agents]

        # 5. Validate & Map
        final_next_steps = []

        # Create a normalized map for case-insensitive lookup
        # Map UPPERCASE display name -> actual node name
        node_map = {}
        for node in registered_nodes:
            display_upper = node.display_name.upper()
            node_map[display_upper] = node.name

            # Robustness: Also allow mapping from the server name directly (e.g. "S3" -> "ToolAgent_s3")
            # If the display name is "ToolAgent_s3", we want to allow "S3".
            # If display name is "ToolAgent_mcp-math", allow "mcp-math" and "mcp_math"

            # 1. Strip 'ToolAgent_' prefix if present
            if display_upper.startswith("TOOLAGENT_"):
                short_name = display_upper.replace("TOOLAGENT_", "")
                node_map[short_name] = node.name
                node_map[short_name.replace("-", "_")] = node.name
                node_map[short_name.replace("_", "-")] = node.name

            # 2. Allow base agent name (snake_case)
            node_map[node.name.upper()] = node.name

        # Map Workflows
        for w in workflows:
            node_map[f"TEAM_{w.name.upper()}"] = w.name

        # Add static nodes to map
        node_map["QA"] = "qa"

        for decision_upper in decisions:
            if decision_upper in node_map:
                final_next_steps.append(node_map[decision_upper])

        # 6. Guardrails: QA Exclusivity
        # If any specialized agent is selected, QA should NOT be run in parallel.
        if not final_next_steps:
            final_next_steps = ["qa"]

        # Return (next_steps, plan)
        return final_next_steps, decision.plan
