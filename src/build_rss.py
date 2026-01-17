from store import connect
from datetime import datetime, timezone
from email.utils import format_datetime
from dateutil import parser as dtparser
from xml.sax.saxutils import escape as xml_escape

SITE_URL = "https://xiaolin-econ.github.io/ai-digest/"
FEED_URL = "https://xiaolin-econ.github.io/ai-digest/rss.xml"


def esc(x: str) -> str:
    # Use xml.sax.saxutils.escape to handle &, <, > and also escape quotes for attributes
    if x is None:
        return ""
    return xml_escape(str(x), entities={"'": "&apos;", '"': "&quot;"})


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
        "SELECT source, title, url, published, summary, ai_summary FROM items ORDER BY published DESC LIMIT 50"
    ).fetchall()

    now_rfc822 = format_datetime(datetime.now(timezone.utc))

    items_xml = []
    for source, title, url, published, summary, ai_summary in rows:
        pub_rfc822 = to_rfc822(published)
        combined = f"{source} - {(summary or '')[:400]}"
        if ai_summary:
            combined = combined + "\n\nAI summary: " + (ai_summary or "")
        items_xml.append("""
<item>
  <title>%s</title>
  <link>%s</link>
  <guid>%s</guid>
  <pubDate>%s</pubDate>
  <description>%s</description>
</item>
""" % (esc(title), esc(url), esc(url), esc(pub_rfc822), esc(combined)))

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>AI Research Digest</title>
  <link>{esc(SITE_URL)}</link>
  <description>Curated AI research + releases</description>
  <lastBuildDate>{esc(now_rfc822)}</lastBuildDate>
  <atom:link href="{esc(FEED_URL)}" rel="self" type="application/rss+xml" xmlns:atom="http://www.w3.org/2005/Atom"/>
  {''.join(items_xml)}
</channel>
</rss>
"""
    with open("rss.xml", "w", encoding="utf-8") as fh:
        fh.write(rss)
    print("Wrote rss.xml")


if __name__ == "__main__":
    main()
