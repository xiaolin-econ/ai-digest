import sqlite3
from contextlib import closing

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  id TEXT PRIMARY KEY,
  source TEXT,
  title TEXT,
  url TEXT,
  published TEXT,
  summary TEXT
);
"""

def connect(db_path="data/items.sqlite"):
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    return conn

def upsert_items(conn, items):
    with closing(conn.cursor()) as cur:
        for it in items:
            cur.execute(
                "INSERT OR IGNORE INTO items (id, source, title, url, published, summary) VALUES (?,?,?,?,?,?)",
                (it["id"], it["source"], it["title"], it["url"], it.get("published", ""), it.get("summary", ""))
            )
    conn.commit()
