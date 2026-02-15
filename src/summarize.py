import re
import logging
import os
from typing import Optional
from store import connect, set_ai_summary
from llm import summarize_with_gemini, ITEM_PROMPT, DIGEST_PROMPT

logger = logging.getLogger(__name__)


_sentence_split_re = re.compile(r"(?<=[.!?])\s+")


def summarize_text(text: str, max_sentences: int = 2, max_chars: int = 400) -> str:
    """A lightweight extractive summarizer:

    - Splits text into sentences and returns the first `max_sentences` sentences.
    - Falls back to a truncation if the result is too long.

    This is intentionally simple (no external models) and gives a short preview suitable
    as a quick "AI-style" summary. For abstractive summaries, integrate an LLM API.
    """
    if not text:
        return ""

    # Normalize whitespace
    text = " ".join(text.split())

    sentences = _sentence_split_re.split(text)
    if not sentences:
        summary = text[:max_chars]
        return summary

    chosen = sentences[:max_sentences]
    summary = " ".join(chosen).strip()
    if len(summary) > max_chars:
        return summary[: max_chars - 1].rsplit(" ", 1)[0] + "…"
    return summary


def digest_summary(texts: list[str], max_sentences: int = 3, max_chars: int = 800) -> str:
    """Build an overall digest summary from a list of per-item summary strings.

    Tries Gemini first (if USE_GEMINI is set), falls back to extractive.
    """
    if not texts:
        return ""
    concat = "\n\n".join(texts[:20])
    use_gemini = os.environ.get("USE_GEMINI", "0") in ("1", "true", "True")
    if use_gemini:
        try:
            return summarize_with_gemini(concat, max_tokens=200, system_prompt=DIGEST_PROMPT)
        except Exception:
            logger.exception("Gemini digest summary failed, falling back to extractive")
    return summarize_text(concat, max_sentences=max_sentences, max_chars=max_chars)


def main(dry_run: bool = False):
    logging.basicConfig(level=logging.INFO)
    conn = connect()
    cur = conn.cursor()
    # Select items that don't yet have an ai_summary (NULL or empty)
    rows = cur.execute(
        "SELECT id, title, summary, url FROM items WHERE ai_summary IS NULL OR ai_summary = ''"
    ).fetchall()

    if not rows:
        print("No items to summarize.")
        return

    print(f"Generating summaries for {len(rows)} items...")
    for item_id, title, summary, url in rows:
        source_text = summary or title or url or ""
        use_gemini = os.environ.get("USE_GEMINI", "0") in ("1", "true", "True")
        s = ""
        if use_gemini:
            try:
                # Use the configured Google Gemini (or other) LLM endpoint. The implementation
                # reads credentials and endpoint from environment variables. We will fall back
                # to the local extractive summarizer on any error.
                s = summarize_with_gemini(source_text, system_prompt=ITEM_PROMPT)
            except Exception:
                logger.exception("LLM summarization failed, falling back to extractive for %s", item_id)
                s = summarize_text(source_text)
        else:
            s = summarize_text(source_text)
        if not s:
            continue
        if dry_run:
            print(f"- {item_id}: {s}")
        else:
            try:
                set_ai_summary(conn, item_id, s)
            except Exception:
                logger.exception("Failed to set ai_summary for %s", item_id)

    print("Done.")


if __name__ == "__main__":
    main()
