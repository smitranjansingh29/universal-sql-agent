import requests
import json

API = "http://127.0.0.1:8000"

QUESTIONS = [
    "How many orders are there?",
    "What is the total revenue from all orders?",
    "Which user placed the most orders?",
    "Show me the top 3 orders by total amount.",
    "List all users who have not placed any orders.",
]

for q in QUESTIONS:
    print("=" * 70)
    print("Q:", q)
    r = requests.post(
        f"{API}/api/connections/1/query", json={"question": q}, timeout=60
    )
    if r.status_code != 200:
        print("HTTP", r.status_code, r.text[:300])
        continue
    data = r.json()
    print("SQL:", data.get("sql"))
    print("ROWS:", data.get("rows")[:5], "... total", data.get("row_count"))
    print("CHART:", data.get("chart"))
    print("ATTEMPTS:", data.get("attempts"))
    print("SUMMARY:", data.get("summary"))
    if data.get("error"):
        print("ERROR:", data.get("error"), "|", data.get("detail"))
    print()
