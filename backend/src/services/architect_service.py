import logging
from typing import Any, Dict

import orjson

from brain.prompts import ARCHITECT_PROMPT
from brain.registry import AgentRegistry
from models.architect import GraphConfig
from services.tools import tool_service
from utils.pii import masker

logger = logging.getLogger(__name__)



class ArchitectService:
    """
    Standard SOC: Business Logic for high-level plan decomposition.
    """

    def __init__(self):
        self.registry = AgentRegistry()

    async def create_plan(self, request_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decomposes the goal into a structured plan using available agents.
        """
        # 1. Mask PII in goal/context (Done in prompt construction now for safety)
        # goal = masker.mask(payload.get("goal", ""))
        # context = masker.mask(payload.get("context", ""))
        # 1. Get available nodes (Workflows ONLY)
        # We explicitly DO NOT fetch individual agents to prevent reuse/pollution.
        # We only want to allow reusing other Superagents (Workflows) as valid sub-nodes.
        available_workflows = self.registry.get_workflows()
        workflow_descriptions = [f"- {w.name} (Sub-Team): {w.description}" for w in available_workflows]
        nodes_text = "\n".join(workflow_descriptions) if workflow_descriptions else "No existing sub-teams found."

        # 1.b Get Available MCP Tools
        server_tool_map = await tool_service.get_server_tool_map()

        tools_text_parts = []
        for server, tools in server_tool_map.items():
            if not tools:
                continue

            # Check for error
            if len(tools) == 1 and "error" in tools[0]:
                tools_text_parts.append(f"Server: {server} (OFFLINE/UNREACHABLE)")
                tools_text_parts.append(f"  - Error: {tools[0]['error']}")
            else:
                tools_text_parts.append(f"Server: {server}")
                for t in tools:
                    tools_text_parts.append(f"  - {t['name']}: {t['description']}")

            tools_text_parts.append("")  # Spacer

        tools_text = "\n".join(tools_text_parts) if tools_text_parts else "No external tools available."

        # 2. Construct Prompt
        # Use v2.0 Hardened Prompt (XML + JSON + Tri-State Reflection)
        # Use masked payload goal as the request
        safe_request = masker.mask(payload.get("goal", ""))
        full_prompt = ARCHITECT_PROMPT.format(request=safe_request, nodes_text=nodes_text, tools_text=tools_text)

        # 3. Call LLM
        # Mask PII in user request before sending to LLM (Already handled if prompt is simple string, but valid to check)
        # Note: 'prompt' here IS the user request.

        # QwenLLM.call returns a string directly
        # CRITICAL FIX: Use async call to avoid blocking the event loop
        content = await self.llm.acall(full_prompt)

        # 4. Parse JSON
        try:
            # Basic cleanup for common LLM markdown wrapping
            clean_content = content.replace("```json", "").replace("```", "").strip()

            # Robust cleaning: Remove comments (// and /* */)
            import re

            # Remove // comments but keep http://
            clean_content = re.sub(r"(?<!:)//.*", "", clean_content)
            # Remove /* */ comments
            clean_content = re.sub(r"/\*.*?\*/", "", clean_content, flags=re.DOTALL)

            # Fallback: attempt to find first { and last }
            first_brace = clean_content.find("{")
            last_brace = clean_content.rfind("}")
            if first_brace != -1 and last_brace != -1:
                clean_content = clean_content[first_brace : last_brace + 1]

            data = orjson.loads(clean_content)
            config = GraphConfig(**data)
        except Exception as e:
            # Log the raw content for debugging
            print(f"Architect Parse Error: {e}\nRaw Content: {content}")
            raise ValueError(f"Failed to parse Architect response: {e}")

        # 5b. Tool Enforcement (Auto-bind Tools to Roles)
        # Ensure 'creator' agents have file access
        for node in config.nodes:
            # Check corresponding definition or registry entry
            # (Simplification: Just check node type/name strings for keywords)
            role_keywords = ["coder", "architect", "writer", "generator", "engineer"]
            if any(k in node.id.lower() or k in node.type.lower() for k in role_keywords):
                # Ensure they have file access (which triggers 'filesystem' MCP loading in Registry)
                # This is cleaner than manually appending tool names, as the Registry handles the MCP connection.
                node.config["files_access"] = True

                # Also ensure verbose logging for debugging
                if "verbose" not in node.config:
                    node.config["verbose"] = True

        # 5. Validate Nodes
        # Start with registry agents? NO. We only allow Workflows or Newly Defined agents.
        # We initialized `available_workflows` at the start of the method.
        # So we validate against that + definitions.

        valid_types = {w.name for w in available_workflows}

        # Add newly defined agents
        if config.definitions:
            valid_types.update(d.name for d in config.definitions)

        # Explicitly allow built-in types
        valid_types.add("supervisor")

        used_types = [n.type for n in config.nodes]
        invalid_types = [t for t in used_types if t not in valid_types]

        if invalid_types:
            raise ValueError(f"Architect generated invalid node types: {invalid_types}")

        # 6. Validate No "Undefined" Hallucinations
        # Sometimes LLMs output the string "undefined" as a type or id
        if any(n.id.lower() == "undefined" for n in config.nodes):
            raise ValueError("Architect generated a node with ID 'undefined'")

        if any(n.type.lower() == "undefined" for n in config.nodes):
            raise ValueError("Architect generated a node with Type 'undefined'")

        return config
