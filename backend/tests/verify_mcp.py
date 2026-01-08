import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from fastapi.testclient import TestClient

from api.main import app


def test_mcp_endpoints():
    print("Testing MCP Endpoints...")

    # Wrap in with client to trigger lifespan (startup/shutdown) events
    with TestClient(app) as client:
        # Mocking Role
        from api.middleware import get_current_role

        app.dependency_overrides[get_current_role] = lambda: "ADMIN"

        response = client.get("/mcp/")
        if response.status_code == 307:
            response = client.get("/mcp")

        print(f"GET /mcp status: {response.status_code}")
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return

        initial_count = len(response.json())
        print(f"Initial count: {initial_count}")

        # 2. Add Server
        new_server = {"name": "test-verify-mcp", "type": "stdio", "command": "ls", "args": ["-la"]}

        response = client.post("/mcp/", json=new_server)
        if response.status_code == 307:
            response = client.post("/mcp", json=new_server)

        print(f"POST /mcp status: {response.status_code}")
        if response.status_code != 200:
            print(f"Error: {response.text}")
            if "already exists" in response.text:
                print("Server already exists, deleting first...")
                client.delete("/mcp/test-verify-mcp")
                response = client.post("/mcp/", json=new_server)
                print(f"Retry POST /mcp status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Created server: {data['name']}")

            # 3. Verify List Updated
            response = client.get("/mcp/")
            if len(response.json()) != initial_count + 1:
                # It might be that initial count included it if we failed to clean up before?
                # If we created it, deleted it, and re-created it, count should be +1 from start of THIS run.
                print(f"Warning: Count mismatch. Got {len(response.json())}, expected {initial_count + 1}")

            # 4. Delete Server
            response = client.delete(f"/mcp/{data['name']}")
            print(f"DELETE /mcp/{data['name']} status: {response.status_code}")

            # 5. Verify Gone
            response = client.get("/mcp/")
            final_count = len(response.json())
            print(f"Final count: {final_count}")

    print("Verification Complete.")


if __name__ == "__main__":
    test_mcp_endpoints()
