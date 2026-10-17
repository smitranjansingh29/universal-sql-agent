import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect("test.db")
c = conn.cursor()

# Clear existing (safe for test db)
c.execute("DELETE FROM orders")
c.execute("DELETE FROM users")

# Add 5 users
users = [
    (1, "Alice", "alice@example.com"),
    (2, "Bob", "bob@example.com"),
    (3, "Carol", "carol@example.com"),
    (4, "Dave", "dave@example.com"),
    (5, "Eve", "eve@example.com"),
]
c.executemany("INSERT INTO users (id, name, email) VALUES (?, ?, ?)", users)

# Add 20 orders across the last 60 days
base = datetime.now() - timedelta(days=60)
orders = []
for i in range(20):
    user_id = (i % 5) + 1
    total = round(10.0 + i * 5.25, 2)
    created_at = (base + timedelta(days=i * 3)).strftime("%Y-%m-%d")
    orders.append((i + 1, user_id, total, created_at))

c.executemany(
    "INSERT INTO orders (id, user_id, total, created_at) VALUES (?, ?, ?, ?)",
    orders,
)

conn.commit()
conn.close()
print(f"Seeded {len(users)} users and {len(orders)} orders into test.db")
