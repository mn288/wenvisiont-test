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
        nodes_text = "\n".join(node_descriptions)

        # 2. Construct Prompt
        system_prompt = f"""You are an Expert AI Architect. Your goal is to design a multi-agent workflow based on the user's request.
You MUST use ONLY the available nodes from the registry below. Do not invent new node types.

Available Nodes:
{nodes_text}

Output Format:
Return a strictly valid JSON object adhering to this structure:
{{
  "name": "Superagent Name",
  "description": "What this workflow does",
  "nodes": [
    {{ "id": "node1", "type": "registry_node_name", "config": {{}} }}
  ],
  "edges": [
    {{ "source": "node1", "target": "node2" }}
  ]
}}

Rules:
1. 'type' MUST match a name from the Available Nodes list exactly.
2. Ensure the graph is logical (DAG).
3. Always include a 'supervisor' node if complex coordination is needed, or chain them linearly if simple.
4. If the user asks for something impossible with current nodes, try to approximate or return a minimal valid graph.
"""

        # 3. Call LLM
        # Mask PII in user request before sending to LLM
        safe_prompt = mask_pii(prompt)

        # QwenLLM.call returns a string directly
        content = llm.call(system_prompt + "\n\nUser Request: " + safe_prompt)

        # 4. Parse JSON
        # Clean up code blocks if present
        clean_content = content.replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(clean_content)
            config = GraphConfig(**data)
        except Exception as e:
            # Simple retry or fallback could go here
            raise ValueError(f"Failed to parse Architect response: {e} | Content: {clean_content}")

        # 5. Validate Nodes
        used_types = [n.type for n in config.nodes]
        invalid_types = self.registry.validate_node_names(used_types)

        if invalid_types:
            raise ValueError(f"Architect generated invalid node types: {invalid_types}")

        return config
