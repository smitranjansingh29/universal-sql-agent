import requests
import json

API = "http://127.0.0.1:8000"  # change from localhost to 127.0.0.1

# Make sure uvicorn is running
r = requests.post(
    f"{API}/api/connections/1/query", json={"question": "How many orders are there?"}
)
print(json.dumps(r.json(), indent=2))
