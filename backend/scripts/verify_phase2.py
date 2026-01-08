import asyncio
import os
import sys

from fastapi.testclient import TestClient

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app
from brain.registry import AgentRegistry
from core.database import pool


async def verify():
    print("--- Verifying Phase 2: Architecture Lift ---")

    # 1. DB Connection
    print("\n1. Checking Database Connection...")
    await pool.open()
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT count(*) FROM superagents")
                row = await cur.fetchone()
                count = row[0]
                print(f"✅ 'superagents' table exists. Count: {count}")
                if count == 0:
                    print("⚠️ Warning: No agents found in DB (Migration might have failed or empty)")
                else:
                    print("✅ Agents found in DB.")
    except Exception as e:
        print(f"❌ DB Check Failed: {e}")
        return

    # 2. Agent Registry
    print("\n2. Checking Agent Registry...")
    registry = AgentRegistry()
    await registry.load_agents()
    agents = registry.get_all()
    print(f"✅ Registry loaded {len(agents)} agents.")
    for a in agents:
        print(f"   - {a.name}")

    if len(agents) > 0:
        print("✅ AgentRegistry is successfully reading from DB.")
    else:
        print("❌ AgentRegistry is empty.")

    # 3. Stats API
    print("\n3. Checking Stats API (via TestClient)...")
    client = TestClient(app)
    # Note: accessing /stats might require DB pool to be open in the app context.
    # TestClient doesn't run the lifespan events automatically in older versions,
    # but since we opened the pool globally above, it might work if the endpoint uses the same pool instance.

    try:
        response = client.get("/stats/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ /stats endpoint returned 200: {data}")
            if "total_invocations" in data and "active_agents" in data:
                print("✅ Stats schema is correct.")
        else:
            print(f"❌ /stats endpoint failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Stats API Check Failed: {e}")

    await pool.close()
    print("\n--- Verification Complete ---")


if __name__ == "__main__":
    asyncio.run(verify())
