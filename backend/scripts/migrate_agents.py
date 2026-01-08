"""
Migration Script: YAML Agents -> Database
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

import yaml
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

# Add parent directory to path to allow importing src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.registry import NodeConfig
from core.config import settings
from models.agents import SuperAgent

# Ensure async driver
db_url = settings.database_url
if db_url.startswith("postgresql://") and "psycopg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://")

engine = create_async_engine(db_url, echo=False)

AGENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "config", "agents")


async def migrate_agents():
    print(f"Starting migration from {AGENTS_DIR}...")

    if not os.path.exists(AGENTS_DIR):
        print("Agents directory not found. Skipping.")
        return

    yaml_files = [f for f in os.listdir(AGENTS_DIR) if f.endswith(".yaml") or f.endswith(".yml")]
    print(f"Found {len(yaml_files)} YAML agent files.")

    async with AsyncSession(engine) as session:
        for filename in yaml_files:
            file_path = os.path.join(AGENTS_DIR, filename)
            try:
                with open(file_path, "r") as f:
                    data = yaml.safe_load(f)

                # Validate against Pydantic model
                node_config = NodeConfig(**data)

                # Check if already exists
                statement = select(SuperAgent).where(SuperAgent.name == node_config.name)
                results = await session.exec(statement)
                existing_agent = results.first()

                if existing_agent:
                    print(f"Agent {node_config.name} already in DB. Updating...")
                    existing_agent.config = node_config.model_dump()
                    existing_agent.updated_at = datetime.now(timezone.utc)
                    session.add(existing_agent)
                else:
                    print(f"Insert new agent: {node_config.name}")
                    new_agent = SuperAgent(id=uuid4(), name=node_config.name, config=node_config.model_dump())
                    session.add(new_agent)

            except Exception as e:
                print(f"FAILED to migrate {filename}: {e}")

        await session.commit()
    print("Migration complete.")


if __name__ == "__main__":
    asyncio.run(migrate_agents())
