import requests
import json

API = "http://localhost:8000"

# Test 1: health
r = requests.get(f"{API}/api/health")
print("HEALTH:", r.status_code, r.json())

# Test 2: create connection with the SQLite file
payload = {"name": "Test SQLite", "url": "sqlite:///./test.db"}
r = requests.post(f"{API}/api/connections", json=payload)
print("\nCREATE CONNECTION:", r.status_code)
print(json.dumps(r.json(), indent=2))

# Test 3: list connections
r = requests.get(f"{API}/api/connections")
print("\nLIST CONNECTIONS:", r.status_code)
print(json.dumps(r.json(), indent=2))
