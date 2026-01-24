import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from core.database import pool


async def main():
    try:
        await pool.open()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT value FROM configurations WHERE key = 'infrastructure_config'")
                row = await cur.fetchone()
                print("Config:", row[0] if row else "None")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
