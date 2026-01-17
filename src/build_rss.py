from store import connect
from datetime import datetime, timezone

def esc(x: str) -> str:
    return (x or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def main():
    conn = connect()
    rows = conn.cursor().execute(
        "SELECT source, title, url, published, summary FROM items ORDER BY published DESC LIMIT 50"
    ).fetchall()

    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")

    items_xml = []
    for source, title, url, published, summary in rows:
        pub = published or now
        desc = f"{source} - {(summary or '')[:500]}"
        items_xml.append(f"""
<item>
  <title>{esc(title)}</title>
  <link>{esc(url)}</link>
  <guid>{esc(url)}</guid>
  <pubDate>{esc(pub)}</pubDate>
  <description>{esc(desc)}</description>
</item>
""".strip())

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>AI Research Digest</title>
  <link>https://example.com/</link>
  <description>Curated AI research + releases</description>
  <lastBuildDate>{now}</lastBuildDate>
  {''.join(items_xml)}
</channel>
</rss>
"""
    open("rss.xml", "w", encoding="utf-8").write(rss)
    print("Wrote rss.xml")

if __name__ == "__main__":
    main()
