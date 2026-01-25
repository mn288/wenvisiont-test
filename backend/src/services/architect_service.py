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
1. **Star Graph Pattern (REQUIRED):**
   - For any multi-step task, you MUST use a central 'supervisor' node to coordinate.
   - Connect ALL agents to the 'supervisor' node (bi-directional edges not strictly needed if supervisor routes).
   - Do NOT create linear chains (A -> B -> C) unless it is a very simple pipeline. Prefer Supervisor -> A, Supervisor -> B.
2. Prefer using Available Nodes if they fit the requirement.
3. If available nodes are insufficient, define NEW agents in 'definitions'.
4. **Dependency Management:**
   - If Agent B depends on Agent A's output, the Supervisor will handle the data passing.
   - Ensure Agent B's task description explicit mentions "using the context/output from Agent A".
5. **MoA & DyLAN Configuration:**
   - **Relationship Strategy**: Agents are generally equals. Assign `importance_score` (0.0-1.0) to guide the Supervisor.
     - Critical Path / Decision Makers: 0.8 - 1.0
     - Support / Research / Workers: 0.4 - 0.7
   - **Task Domains**: Assign specific keywords (e.g., "coding", "qa", "legal", "web_search", "planning") to `task_domains`.
   - **Self-Reflection**: Set `use_reflection: true` for agents that generate complex output (Code, Long-form Writing) to enable a self-critique loop.

Output Format:
Return a strictly valid JSON object:
{{
  "name": "Superagent Name",
  "description": "What this workflow does",
  "nodes": [
    {{ "id": "supervisor", "type": "supervisor", "config": {{}} }},
    {{ "id": "node1", "type": "registry_name_or_new_def_name", "config": {{}} }}
  ],
  "edges": [
    {{ "source": "supervisor", "target": "node1" }},
    {{ "source": "node1", "target": "supervisor" }}
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
         "files_access": true,
         "importance_score": 0.8, // 0.0 to 1.0 (Higher = more likely to be chosen by DyLAN)
         "task_domains": ["domain1", "domain2"], // Keywords for routing e.g. ["coding", "python"]
         "use_reflection": true // Enable for complex generation tasks (Code/Research)
       }},
       "task": {{
         "description": "Must mention {{research_output}} or {{request}} to receive context.",
         "expected_output": "..."
       }}
     }}
  ]
}}
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
