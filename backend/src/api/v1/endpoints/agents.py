import os
from typing import List

import yaml
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from src.brain.registry import AgentRegistry, NodeConfig
from src.crew.agents import llm

router = APIRouter()

AGENTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "config", "agents"
)


class AgentListItem(BaseModel):
    name: str
    role: str
    description: str


class GenerateAgentRequest(BaseModel):
    prompt: str = Field(..., description="Description of the agent to generate")
    files_access: bool = False
    s3_access: bool = False
    mcp_servers: List[str] = []


@router.get("/", response_model=List[NodeConfig])
async def list_agents():
    """List all available agents."""
    registry = AgentRegistry()
    # Ensure fresh load if needed, but registry handles it on init.
    # For dynamic behavior, we might want to force reload or rely on explicit reloads.
    # registry.reload() # Optional: reload on every list to ensure consistency with disk

    return registry.get_all()


@router.get("/{name}", response_model=NodeConfig)
async def get_agent(name: str):
    """Get specific agent configuration."""
    registry = AgentRegistry()
    config = registry.get_config(name)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")
    return config


@router.post("/", response_model=NodeConfig)
async def create_or_update_agent(config: NodeConfig, background_tasks: BackgroundTasks):
    """Create or update an agent configuration."""
    file_path = os.path.join(AGENTS_DIR, f"{config.name}.yaml")

    # Convert Pydantic model to dict, exclude defaults to keep YAML clean
    data = config.model_dump(exclude_none=True)

    # Save to YAML
    try:
        with open(file_path, "w") as f:
            yaml.dump(data, f, sort_keys=False, default_flow_style=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save agent config: {str(e)}")

    # Reload registry
    AgentRegistry().reload()

    # Reload Graph to pick up new agent
    from src.services.graph_service import GraphService

    await GraphService.get_instance().reload_graph()

    return config


@router.delete("/{name}")
async def delete_agent(name: str):
    """Delete an agent configuration."""
    file_path = os.path.join(AGENTS_DIR, f"{name}.yaml")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Agent file not found")

    try:
        os.remove(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete agent file: {str(e)}")

    # Reload registry
    AgentRegistry().reload()

    # Reload Graph to remove agent
    from src.services.graph_service import GraphService

    await GraphService.get_instance().reload_graph()

    return {"message": f"Agent {name} deleted"}


@router.post("/generate", response_model=NodeConfig)
async def generate_agent(request: GenerateAgentRequest):
    """Generate an agent configuration using LLM."""

    # 1. Fetch "defaults" or "infrastructure_config" from DB
    infra_context = ""
    from src.core.database import pool

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT value FROM configurations WHERE key = 'infrastructure_config'")
                row = await cur.fetchone()
                if row:
                    infra_config = row[0]
                    # Extract relevant info to add to context
                    infra_context = f"\nINFRASTRUCTURE CONTEXT (The user has these global defaults):\n{infra_config}\n"
    except Exception as e:
        print(f"Warning: Failed to fetch infra config: {e}")

    prompt = f"""
    You are an expert generic agent configuration generator.
    Generate a valid YAML configuration for a CrewAI agent based on this description:
    "{request.prompt}"

    {infra_context}
    
    The configuration must match this Pydantic schema structure (JSON equivalent):
    {{
        "name": "agent_name_snake_case",
        "display_name": "Human Readable Name",
        "description": "Short description",
        "output_state_key": "unique_output_key",
        "agent": {{
            "role": "Role Name",
            "goal": "Goal description",
            "backstory": "Backstory...",
            "verbose": true,
            "allow_delegation": false,
            "tools": [],
            "mcp_servers": {request.mcp_servers},
            "files_access": {str(request.files_access).lower()},
            "s3_access": {str(request.s3_access).lower()}
        }},
        "task": {{
            "description": "Task description... IMPORTANT: You MUST include {{request}} and {{research_output}} placeholders in the description string so the agent receives the user input and context.",
            "expected_output": "Expected output...",
            "async_execution": true
        }}
    }}
    
    Return ONLY the valid YAML string. No markdown code blocks.
    """

    try:
        response = llm.call(messages=[{"role": "user", "content": prompt}])
        yaml_content = response.replace("```yaml", "").replace("```", "").strip()

        # Validate by parsing
        data = yaml.safe_load(yaml_content)
        config = NodeConfig(**data)

        return config

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate agent: {str(e)}")


@router.get("/mcp/servers")
async def list_mcp_servers():
    """List available MCP servers (mock/stub for now)."""
    # In a real app, this would query the DB or config
    return ["local", "fastmcp"]
