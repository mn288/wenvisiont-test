import json

from brain.registry import AgentRegistry
from crew.agents import llm
from models.architect import GraphConfig
from utils.pii import mask_pii


class ArchitectService:
    def __init__(self):
        self.registry = AgentRegistry()

    async def generate_graph_config(self, prompt: str) -> GraphConfig:
        # 1. Get available nodes
        available_nodes = self.registry.get_all()
        node_descriptions = [f"- {n.name}: {n.description}" for n in available_nodes]
        nodes_text = "\n".join(node_descriptions) if node_descriptions else "No existing agents found."

        # 2. Construct Prompt
        system_prompt = f"""You are an Expert AI Architect. Your goal is to design a multi-agent workflow based on the user's request.

Available Nodes (Registry):
{nodes_text}

Instructions:
1. Prefer using Available Nodes if they fit the requirement.
2. **CRITICAL**: If the available nodes are insufficient or empty, you MUST define NEW agents in the 'definitions' list.
3. The 'type' in 'nodes' list must match either an Available Node name OR a name defined in 'definitions'.

Output Format:
Return a strictly valid JSON object adhering to this structure:
{{
  "name": "Superagent Name",
  "description": "What this workflow does",
  "nodes": [
    {{ "id": "node1", "type": "registry_name_or_new_def_name", "config": {{}} }}
  ],
  "edges": [
    {{ "source": "node1", "target": "node2" }}
  ],
  "definitions": [
     // Only if defining NEW agents
     {{
       "name": "agent_name_snake_case",
       "display_name": "Agent Name",
       "description": "Agent description",
       "output_state_key": "step_output",
       "agent": {{
         "role": "...",
         "goal": "...",
         "backstory": "...",
         "tools": [],
         "verbose": true,
         "allow_delegation": false,
         "files_access": true
       }},
       "task": {{
         "description": "...",
         "expected_output": "..."
       }}
     }}
  ]
}}

Rules:
1. Ensure the graph is logical (DAG).
2. Always include a 'supervisor' node if complex coordination is needed.
3. Keep 'definitions' empty if you only use existing nodes.
"""

        # 3. Call LLM
        # Mask PII in user request before sending to LLM
        safe_prompt = mask_pii(prompt)

        # QwenLLM.call returns a string directly
        content = llm.call(system_prompt + "\n\nUser Request: " + safe_prompt)

        # 4. Parse JSON
        # Clean up code blocks if present
        clean_content = content.replace("```json", "").replace("```", "").strip()

        # Robust cleaning: Remove comments (// and /* */)
        import re
        # Remove // comments but keep http://
        clean_content = re.sub(r'(?<!:)//.*', '', clean_content)
        # Remove /* */ comments
        clean_content = re.sub(r'/\*.*?\*/', '', clean_content, flags=re.DOTALL)
        
        try:
            data = json.loads(clean_content)
            config = GraphConfig(**data)
        except Exception as e:
            # Simple retry or fallback could go here
            raise ValueError(f"Failed to parse Architect response: {e} | Content: {clean_content}")

        # 5. Validate Nodes
        # Start with registry agents
        valid_types = {n.name for n in available_nodes}
        
        # Add workflows
        valid_types.update(w.name for w in self.registry.get_workflows())

        # Add newly defined agents
        if config.definitions:
            valid_types.update(d.name for d in config.definitions)

        # Explicitly allow built-in types
        valid_types.add("supervisor")

        used_types = [n.type for n in config.nodes]
        invalid_types = [t for t in used_types if t not in valid_types]

        if invalid_types:
            raise ValueError(f"Architect generated invalid node types: {invalid_types}")

        return config
