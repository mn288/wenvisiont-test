import glob
import os

import yaml

from brain.registry import AgentRegistry, NodeConfig
from models.mcp import MCPServerCreate
from services.mcp import mcp_service

CONFIG_DIR = "/app/backend/src/config/agents"


async def seed_agents():
    """
    Reads all YAML files from backend/src/config/agents and registers them via AgentRegistry.
    This ensures the database is populated with the default dynamic agents on startup.
    """
    if not os.path.exists(CONFIG_DIR):
        print(f"SEEDER: Config directory not found at {CONFIG_DIR}")
        # Fallback for local dev if not running in Docker or path differs
        local_path = "backend/src/config/agents"
        if os.path.exists(local_path):
            CONFIG_DIR_PATH = local_path
        else:
            print("SEEDER: No agent config found. Skipping seed.")
            return
    else:
        CONFIG_DIR_PATH = CONFIG_DIR

    registry = AgentRegistry()

    # Check if we already have agents?
    # Actually, we want to UPSERT so valid config always matches code.
    # But if you only want to seed on empty, we can check count.
    # For now, let's upsert to ensure latest config changes are reflected.

    files = glob.glob(os.path.join(CONFIG_DIR_PATH, "*.yaml"))
    if not files:
        print("SEEDER: No YAML files found in config/agents.")
        return

    print(f"SEEDER: Found {len(files)} agent configs. seeding...")

    for file_path in files:
        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)

            # Validate and Parse
            # The YAML structure must match NodeConfig
            # We assume the YAMLs are perfectly formed based on the Studio output
            try:
                node_config = NodeConfig(**data)
                await registry.save_agent(node_config)
                print(f"SEEDER: Seeded agent '{node_config.name}'")
            except Exception as e:
                print(f"SEEDER: Failed to parse {file_path}: {e}")

        except Exception as e:
            print(f"SEEDER: Error reading {file_path}: {e}")

    print("SEEDER: Agent seeding complete.")


async def seed_mcp_servers():
    """
    Seeds default MCP servers required for the system to function.
    Specifically: 'filesystem' and 's3' for tool access.

    Architecture:
    These are running as separate containers in Docker Compose.
    Backend connects via SSE (Server-Sent Events).
    """

    # 1. FILESYSTEM SERVER
    try:
        existing = await mcp_service.get_servers_by_names(["filesystem"])
        if not existing:
            print("SEEDER: Creating default 'filesystem' MCP server (SSE)...")

            # Default to Docker DNS name.
            # If running locally without docker network (e.g. uvicorn), user might need to override or use localhost ports.
            # But 'backend' service in docker-compose depends on 'filesystem-mcp'.

            # Check for override env var, else default to docker service name
            fs_url = os.getenv("MCP_FILESYSTEM_URL", "http://filesystem-mcp:8000/sse")

            server_payload = MCPServerCreate(name="filesystem", type="sse", url=fs_url)

            await mcp_service.create_server(server_payload)
            print("SEEDER: 'filesystem' MCP server created successfully.")
    except Exception as e:
        print(f"SEEDER: Failed to seed filesystem MCP: {e}")

    # 2. S3 SERVER
    try:
        existing_s3 = await mcp_service.get_servers_by_names(["s3"])
        if not existing_s3:
            print("SEEDER: Creating default 's3' MCP server (SSE)...")

            s3_url = os.getenv("MCP_S3_URL", "http://s3-mcp:8000/sse")

            server_payload_s3 = MCPServerCreate(name="s3", type="sse", url=s3_url)

            await mcp_service.create_server(server_payload_s3)
            print("SEEDER: 's3' MCP server created successfully.")
    except Exception as e:
        print(f"SEEDER: Failed to seed S3 MCP: {e}")

    # 3. MATH SERVER
    try:
        existing_math = await mcp_service.get_servers_by_names(["mcp-math"])
        if not existing_math:
            print("SEEDER: Creating default 'mcp-math' MCP server (SSE)...")

            math_url = os.getenv("MCP_MATH_URL", "http://mcp-math:8000/sse")

            server_payload_math = MCPServerCreate(name="mcp-math", type="sse", url=math_url)

            await mcp_service.create_server(server_payload_math)
            print("SEEDER: 'mcp-math' MCP server created successfully.")
    except Exception as e:
        print(f"SEEDER: Failed to seed Math MCP: {e}")

    # 4. ANALYSIS SERVER
    try:
        existing_analysis = await mcp_service.get_servers_by_names(["analysis-mcp"])
        if not existing_analysis:
            print("SEEDER: Creating default 'analysis-mcp' MCP server (SSE)...")

            analysis_url = os.getenv("MCP_ANALYSIS_URL", "http://analysis-mcp:8000/sse")

            server_payload_analysis = MCPServerCreate(name="analysis-mcp", type="sse", url=analysis_url)

            await mcp_service.create_server(server_payload_analysis)
            print("SEEDER: 'analysis-mcp' MCP server created successfully.")
    except Exception as e:
        print(f"SEEDER: Failed to seed Analysis MCP: {e}")
    # 5. GCP RAG SERVER
    try:
        existing_rag = await mcp_service.get_servers_by_names(["gcp-rag"])
        if not existing_rag:
            print("SEEDER: Creating default 'gcp-rag' MCP server (STDIO)...")

            # Helper to find python executable and script path
            import sys

            python_exe = sys.executable
            # Relative to /app/backend or cwd
            script_path = os.path.abspath("src/mcp/rag.py")
            if not os.path.exists(script_path):
                # Try relative to this file?
                script_path = "/app/backend/src/mcp/rag.py"

            server_payload_rag = MCPServerCreate(name="gcp-rag", type="stdio", command=python_exe, args=[script_path])

            await mcp_service.create_server(server_payload_rag)
            print("SEEDER: 'gcp-rag' MCP server created successfully.")
    except Exception as e:
        print(f"SEEDER: Failed to seed GCP RAG MCP: {e}")

    # 6. GCP BIGQUERY SERVER (STDIO via Python)
    try:
        existing_bq = await mcp_service.get_servers_by_names(["gcp-bigquery"])
        if not existing_bq:
            print("SEEDER: Creating default 'gcp-bigquery' MCP server (STDIO)...")

            import sys

            python_exe = sys.executable
            script_path = os.path.abspath("src/mcp/bigquery.py")
            if not os.path.exists(script_path):
                script_path = "/app/backend/src/mcp/bigquery.py"

            server_payload_bq = MCPServerCreate(
                name="gcp-bigquery", type="stdio", command=python_exe, args=[script_path]
            )

            await mcp_service.create_server(server_payload_bq)
            print("SEEDER: 'gcp-bigquery' MCP server created successfully.")
    except Exception as e:
        print(f"SEEDER: Failed to seed GCP BigQuery MCP: {e}")
