import sqlite3
from contextlib import closing
from pathlib import Path

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


def connect(db_path: str | None = None):
    """Connect to the SQLite DB. If db_path is None, use the repository's data/items.sqlite

    The function ensures the data directory exists and returns a live connection with the
    table schema applied.
    """
    # Resolve a sensible default path relative to the project root (two levels up from this file)
    base = Path(__file__).resolve().parent.parent
    data_dir = base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    db_file = Path(db_path) if db_path else data_dir / "items.sqlite"
    conn = sqlite3.connect(str(db_file))
    conn.execute(SCHEMA)
    return conn


def upsert_items(conn, items):
    with closing(conn.cursor()) as cur:
        for it in items:
            cur.execute(
                "INSERT OR IGNORE INTO items (id, source, title, url, published, summary) VALUES (?,?,?,?,?,?)",
                (it["id"], it["source"], it["title"], it["url"], it.get("published", ""), it.get("summary", "")),
            )
    conn.commit()


def recent_items(conn, since_iso):
    cur = conn.cursor()
    return cur.execute(
        "SELECT source, title, url, published, summary "
        "FROM items "
        "WHERE published >= ? "
        "ORDER BY published DESC",
        (since_iso,),
    ).fetchall()
