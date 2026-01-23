import glob
import os

import yaml

from brain.registry import AgentRegistry, NodeConfig

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
            with open(file_path, 'r') as f:
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
