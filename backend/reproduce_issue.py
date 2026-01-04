
import requests

base_url = "http://localhost:8000"
thread_id = "thread_1767797173151"
checkpoint_id = "1f0ebd79-cfba-6084-8001-b108a243806e"
new_input = "add full comments on each line of code"
reset_to_step = "senior_python_engineer"

url = f"{base_url}/fork"
params = {
    "thread_id": thread_id,
    "checkpoint_id": checkpoint_id,
    "new_input": new_input,
    "reset_to_step": reset_to_step,
}

try:
    print(f"Sending POST to {url} with params: {params}")
    response = requests.post(url, params=params)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
