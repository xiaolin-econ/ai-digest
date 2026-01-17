import os
import smtplib
import logging
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from html import escape as html_escape
from store import connect, recent_items
from summarize import summarize_text
from llm import summarize_with_gemini

logger = logging.getLogger(__name__)

def build_html(rows):
    parts = []
    parts.append("<h1>AI Research Digest</h1>")
    parts.append(f"<p>{datetime.now().strftime('%B %d, %Y')}</p>")
    # Build an overall AI summary for the digest by combining per-item ai_summary fields
    try:
        combined_texts = [r[5] for r in rows if len(r) > 5 and r[5]]
        if not combined_texts:
            combined_texts = [r[4] for r in rows if len(r) > 4 and r[4]]
        if combined_texts:
            concat = "\n\n".join(combined_texts[:20])  # limit number of items concatenated
            use_gemini = os.environ.get("USE_GEMINI", "0") in ("1", "true", "True")
            if use_gemini:
                try:
                    overall = summarize_with_gemini(concat, max_tokens=200)
                except Exception:
                    logger.exception("Gemini summarization failed, falling back to local summarizer")
                    overall = summarize_text(concat, max_sentences=3, max_chars=800)
            else:
                overall = summarize_text(concat, max_sentences=3, max_chars=800)
            if overall:
                parts.append("<h2>Daily AI Summary</h2>")
                parts.append(f"<p>{html_escape(overall)}</p>")
    except Exception:
        logger.exception("Failed to build overall AI summary")
    parts.append("<hr/>")

    if not rows:
        parts.append("<p>No new items found in the last 24 hours.</p>")
        return "\n".join(parts)

    parts.append("<ol>")
    for source, title, url, published, summary, ai_summary in rows[:40]:
        # Escape content inserted into HTML to avoid broken layout or injection
        src = html_escape(source or "")
        t = html_escape(title or "")
        u = html_escape(url or "", quote=True)
        pub = html_escape(published or "")
        summ = html_escape((summary or "")[:300])
        ai_s = html_escape((ai_summary or "")[:300])
        parts.append(
            f"<li><b>{src}</b>: <a href='{u}'>{t}</a>"
            f"<br/><small>{pub}</small>"
            f"<br/>{summ}"
            + (f"<br/><em>AI summary:</em> {ai_s}" if ai_s else "")
            + "</li><br/>"
        )
    parts.append("</ol>")
    return "\n".join(parts)

def main():
    conn = connect()
    rows = conn.cursor().execute(
        "SELECT source, title, url, published, summary, ai_summary "
        "FROM items "
        "ORDER BY published DESC "
        "LIMIT 15"
    ).fetchall()

    html = build_html(rows)

    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = "AI Research Digest"

    # Validate required env vars
    missing = [k for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS") if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Missing required SMTP env vars: {', '.join(missing)}")

    msg["From"] = os.environ["SMTP_USER"]
    msg["To"] = os.environ.get("DIGEST_TO", os.environ["SMTP_USER"])

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    pwd = os.environ["SMTP_PASS"]

    try:
        with smtplib.SMTP(host, port) as s:
            s.starttls()
            s.login(user, pwd)
            s.sendmail(msg["From"], [msg["To"]], msg.as_string())
        logger.info("Sent digest to %s with %d items", msg["To"], len(rows))
    except Exception:
        logger.exception("Failed to send digest to %s", msg.get("To"))

if __name__ == "__main__":
    main()
