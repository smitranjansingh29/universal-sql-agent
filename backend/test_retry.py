import requests, json

API = "http://127.0.0.1:8000"
# Ask for something that requires a column that doesn't exist -> first attempt likely fails -> retry fixes it
q = "Show me orders with a discount greater than 5%"
r = requests.post(f"{API}/api/connections/1/query", json={"question": q}, timeout=60)
print(json.dumps(r.json(), indent=2))
