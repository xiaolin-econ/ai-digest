import logging
from pathlib import Path
import yaml
import hashlib
import feedparser
import requests
from dateutil import parser as dtparser
from store import connect, upsert_items

logger = logging.getLogger(__name__)

KEYWORDS = [
    "productivity",
    "workflow",
    "copilot",
    "assistant",
    "agent",
    "automation",
    "human-ai",
    "human ai",
    "decision support",
    "knowledge work",
    "office",
    "programming assistant",
    "software engineering",
    "developer productivity",
    "task completion",
    "information retrieval",
    "search assistant",
    "writing",
    "coding",
    "debugging",
]

def is_productivity_paper(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    return any(k in text for k in KEYWORDS)

def stable_id(source, url, title):
    raw = f"{source}|{url}|{title}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def main():
    logging.basicConfig(level=logging.INFO)
    # Resolve feeds.yaml relative to the project root so scripts can be run from any cwd.
    base = Path(__file__).resolve().parent.parent
    feeds_path = base / "feeds.yaml"
    if not feeds_path.exists():
        logger.error("feeds.yaml not found at %s", feeds_path)
        return

    with feeds_path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    items = []

    for s in cfg["sources"]:
        if s.get("type") not in ("rss", "arxiv"):
            continue

        try:
            resp = requests.get(
                s["url"],
                headers={"User-Agent": "Mozilla/5.0 (compatible; ai-digest/1.0)"},
                timeout=30,
            )
            resp.raise_for_status()
            # Use raw bytes to let feedparser detect encoding correctly
            feed = feedparser.parse(resp.content)
        except Exception as ex:
            logger.exception("FAILED to fetch %s -> %s: %s", s.get("name"), s.get("url"), ex)
            continue

        for e in feed.entries[:50]:
            url = e.get("link", "")
            title = (e.get("title") or "").strip()

            published = ""
            if e.get("published"):
                try:
                    published = dtparser.parse(e.published).isoformat()
                except Exception:
                    published = ""

            summary = (e.get("summary") or e.get("description") or "").strip()

            if not is_productivity_paper(title, summary):
                continue

            items.append(
                {
                    "id": stable_id(s["name"], url, title),
                    "source": s["name"],
                    "title": title,
                    "url": url,
                    "published": published,
                    "summary": summary,
                }
            )

    conn = connect()
    upsert_items(conn, items)
    logger.info("Collected %d items", len(items))


if __name__ == "__main__":
    main()
