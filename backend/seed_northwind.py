"""
Load the Northwind sample database into a local SQLite file.
Downloads from a stable public mirror if not already present.
"""

import sqlite3
import urllib.request
from pathlib import Path

NORTHWIND_URL = (
    "https://raw.githubusercontent.com/jpwhite3/northwind-SQLite3/"
    "main/dist/northwind.db"
)
DB_PATH = Path(__file__).parent / "northwind.db"


def download_if_missing():
    if DB_PATH.exists():
        print(f"✓ northwind.db already exists ({DB_PATH.stat().st_size:,} bytes)")
        return
    print(f"Downloading Northwind from {NORTHWIND_URL} ...")
    urllib.request.urlretrieve(NORTHWIND_URL, DB_PATH)
    print(f"✓ Downloaded {DB_PATH.stat().st_size:,} bytes to {DB_PATH}")


def verify():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    tables = [
        r[0]
        for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    ]
    print(f"\n{len(tables)} tables in Northwind:")
    for t in tables:
        count = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        print(f"  {t:20s}  {count:>6d} rows")
    conn.close()


if __name__ == "__main__":
    download_if_missing()
    verify()
    print(f"\n✅ Ready. Register this connection in the app:")
    print(f"   POST /api/connections  with")
    print(f'   {{"name": "Northwind", "url": "sqlite:///./northwind.db"}}')
