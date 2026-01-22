from typing import List

import yaml  # Kept for Generate prompt parsing if needed, or remove if logic changes
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import require_role
from brain.registry import AgentRegistry, NodeConfig
from crew.agents import llm

router = APIRouter()


class GenerateAgentRequest(BaseModel):
    prompt: str = Field(..., description="Description of the agent to generate")
    files_access: bool = False
    s3_access: bool = False
    mcp_servers: List[str] = []


@router.get("/", response_model=List[NodeConfig])
async def list_agents():
    """List all available agents."""
    registry = AgentRegistry()
    return registry.get_all()


@router.get("/summary")
async def get_agents_summary():
    """Get list of registered agents for UI visualization."""
    registry = AgentRegistry()
    agents = registry.get_all()

    return [
        {
            "id": agent.name,
            "label": f"{agent.display_name} Agent",
            "role": agent.agent.role,
            "description": agent.description,
        }
        for agent in agents
    ]


@router.get("/{name}", response_model=NodeConfig)
async def get_agent(name: str):
    """Get specific agent configuration."""
    registry = AgentRegistry()
    config = registry.get_config(name)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")
    return config


@router.post("/", response_model=NodeConfig, dependencies=[Depends(require_role("ADMIN"))])
async def create_or_update_agent(config: NodeConfig, background_tasks: BackgroundTasks):
    """Create or update an agent configuration using Database Persistence."""
    registry = AgentRegistry()

    # Validate MCP servers against tenant config
    if config.agent.mcp_servers:
        from core.database import pool

        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT value FROM configurations WHERE key = 'infrastructure_config'")
                    row = await cur.fetchone()
                    if row:
                        infra_data = row[0] if isinstance(row[0], dict) else {}
                        allowed = infra_data.get("allowed_mcp_servers", [])
                        if allowed:  # Only validate if list is explicitly set
                            invalid = [s for s in config.agent.mcp_servers if s not in allowed]
                            if invalid:
                                raise HTTPException(
                                    status_code=403, detail=f"MCP servers not allowed for this tenant: {invalid}"
                                )
        except HTTPException:
            raise
        except Exception as e:
            print(f"Warning: Failed to validate MCP servers: {e}")

    # Save to DB and Cache
    try:
        await registry.save_agent(config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save agent: {str(e)}")

    # Reload Graph to pick up new agent
    from services.graph_service import GraphService

    await GraphService.get_instance().reload_graph()

    return config


@router.delete("/{name}", dependencies=[Depends(require_role("ADMIN"))])
async def delete_agent(name: str):
    """Delete an agent configuration."""
    registry = AgentRegistry()

    # Check existence
    if not registry.get_config(name):
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        await registry.delete_agent(name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete agent: {str(e)}")

    # Reload Graph to remove agent
    from services.graph_service import GraphService

    await GraphService.get_instance().reload_graph()

    return {"message": f"Agent {name} deleted"}


@router.post("/generate", response_model=NodeConfig, dependencies=[Depends(require_role("ADMIN"))])
async def generate_agent(request: GenerateAgentRequest):
    """Generate an agent configuration using LLM."""

    # 1. Fetch "defaults" or "infrastructure_config" from DB
    infra_context = ""
    from core.database import pool

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

    # Enforce Permissions based on Infrastructure Configuration
    infra_data = infra_config if "infra_config" in locals() and infra_config else {}

    if request.s3_access:
        s3_conf = infra_data.get("s3_access") or infra_data.get("s3_config")
        if not s3_conf:
            raise HTTPException(status_code=403, detail="S3 Access is not configured for this account.")

    if request.files_access:
        local_path = infra_data.get("local_workspace_path")
        if not local_path:
            raise HTTPException(status_code=403, detail="Local File Access is not configured for this account.")

    # MCP Server Validation - Check against allowed_mcp_servers
    if request.mcp_servers:
        allowed = infra_data.get("allowed_mcp_servers", [])
        if allowed:  # Only validate if list is explicitly set
            invalid = [s for s in request.mcp_servers if s not in allowed]
            if invalid:
                raise HTTPException(status_code=403, detail=f"MCP servers not allowed for this tenant: {invalid}")

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
            "description": "Task description... IMPORTANT: You MUST include {{request}} and {{research_output}} placeholders in the description string so the agent receives the user input and context. ADDITIONALLY, specifically instruct the agent to use the 'AsyncFileWriteTool' (or available file write tool) to save any generated code to the file system, rather than just printing it.",
            "expected_output": "Expected output...",
            "async_execution": true
        }}
    }}
    
    IMPORTANT SYNTAX RULES:
    1. Return ONLY the valid YAML string. No markdown code blocks.
    2. YOU MUST DOUBLE QUOTE ALL STRINGS. This is critical for avoiding YAML parsing errors with colons (:) or special characters.
    Example:
    description: "Analyze the request: {{request}}"
    NOT:
    description: Analyze the request: {{request}}
    """

    try:
        response = llm.call(messages=[{"role": "user", "content": prompt}])
        yaml_content = response.replace("```yaml", "").replace("```", "").strip()

        # Validate by parsing
        data = yaml.safe_load(yaml_content)
        config = NodeConfig(**data)

        # FORCE APPEND: Instructions to use file tools if files_access is on
        if config.agent.files_access:
            config.task.description += "\n\nCRITICAL: You MUST use the 'AsyncFileWriteTool' to save any generated code to the file system. Do not just print the code in your final answer; it must be written to a file first."

        return config

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate agent: {str(e)}")


@router.get("/mcp/servers")
async def list_mcp_servers():
    """List available MCP servers from the database."""
    from core.database import pool

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT name FROM mcp_servers ORDER BY name")
                rows = await cur.fetchall()
                return [row[0] for row in rows]
    except Exception as e:
        print(f"Warning: Failed to fetch MCP servers: {e}")
        return []
