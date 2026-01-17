from store import connect
from datetime import datetime, timezone
from email.utils import format_datetime
from dateutil import parser as dtparser

SITE_URL = "https://xiaolin-econ.github.io/ai-digest/"
FEED_URL = "https://xiaolin-econ.github.io/ai-digest/rss.xml"

def esc(x: str) -> str:
    return (x or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def to_rfc822(dt_str: str) -> str:
    # Convert stored dates (ISO or whatever) into RFC-822 for RSS readers.
    if not dt_str:
        return format_datetime(datetime.now(timezone.utc))
    try:
        dt = dtparser.parse(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return format_datetime(dt.astimezone(timezone.utc))
    except Exception:
        return format_datetime(datetime.now(timezone.utc))

def main():
    conn = connect()
    rows = conn.cursor().execute(
        "SELECT source, title, url, published, summary FROM items ORDER BY published DESC LIMIT 50"
    ).fetchall()

    now_rfc822 = format_datetime(datetime.now(timezone.utc))

    items_xml = []
    for source, title, url, published, summary in rows:
        pub_rfc822 = to_rfc822(published)
        desc = f"{source} - {(summary or '')[:500]}"
        items_xml.append(f"""
<item>
  <title>{esc(title)}</title>
  <link>{esc(url)}</link>
  <guid>{esc(url)}</guid>
  <pubDate>{esc(pub_rfc822)}</pubDate>
  <description>{esc(desc)}</description>
</item>
""".strip())

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>AI Research Digest</title>
  <link>{SITE_URL}</link>
  <description>Curated AI research + releases</description>
  <lastBuildDate>{now_rfc822}</lastBuildDate>
  <atom:link href="{FEED_URL}" rel="self" type="application/rss+xml" xmlns:atom="http://www.w3.org/2005/Atom"/>
  {''.join(items_xml)}
</channel>
</rss>
"""
    open("rss.xml", "w", encoding="utf-8").write(rss)
    print("Wrote rss.xml")

if __name__ == "__main__":
    main()
