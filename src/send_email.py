import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from store import connect, recent_items

def build_html(rows):
    parts = []
    parts.append("<h1>AI Research Digest</h1>")
    parts.append(f"<p>{datetime.now().strftime('%B %d, %Y')}</p>")
    parts.append("<hr/>")

    if not rows:
        parts.append("<p>No new items found in the last 24 hours.</p>")
        return "\n".join(parts)

    parts.append("<ol>")
    for source, title, url, published, summary in rows[:40]:
        parts.append(
            f"<li><b>{source}</b>: <a href='{url}'>{title}</a>"
            f"<br/><small>{published}</small>"
            f"<br/>{(summary or '')[:300]}</li><br/>"
        )
    parts.append("</ol>")
    return "\n".join(parts)

def main():
    # last 24 hours
    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    conn = connect()
    rows = recent_items(conn, since)

    html = build_html(rows)

    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = "AI Research Digest"
    msg["From"] = os.environ["SMTP_USER"]
    msg["To"] = os.environ.get("DIGEST_TO", os.environ["SMTP_USER"])

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    pwd = os.environ["SMTP_PASS"]

    with smtplib.SMTP(host, port) as s:
        s.starttls()
        s.login(user, pwd)
        s.sendmail(msg["From"], [msg["To"]], msg.as_string())

    print(f"Sent digest to {msg['To']} with {len(rows)} items")

if __name__ == "__main__":
    main()
