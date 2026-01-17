import yaml
import hashlib
import feedparser
import requests
from dateutil import parser as dtparser
from store import connect, upsert_items

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
    cfg = yaml.safe_load(open("feeds.yaml"))
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
            feed = feedparser.parse(resp.text)
        except Exception as ex:
            print(f"FAILED to fetch {s.get('name')} -> {s.get('url')}: {ex}")
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

            summary = (e.get("summary") or "").strip()

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
    print(f"Collected {len(items)} items")


if __name__ == "__main__":
    main()
