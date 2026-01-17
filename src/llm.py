import os
import time
import random
import requests
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def _extract_text_from_response(resp_json: dict) -> Optional[str]:
    """Try a few heuristics to extract a text string from the JSON response.

    Different LLM providers return different fields. This helper attempts several
    common locations. If none are found, returns None and the caller may fall back.
    """
    # Common patterns used by some providers
    if not isinstance(resp_json, dict):
        return None

    # Example: {"candidates": [{"content": "..."}, ...]}
    if "candidates" in resp_json and isinstance(resp_json["candidates"], list):
        try:
            first = resp_json["candidates"][0]
            if isinstance(first, dict) and "content" in first:
                return first["content"]
        except Exception:
            pass

    # Example: {"output": {"text": "..."}} or {"output": "..."}
    out = resp_json.get("output")
    if isinstance(out, dict) and "text" in out:
        return out["text"]
    if isinstance(out, str):
        return out

    # Example: {"summary": "..."} or {"text": "..."}
    for k in ("summary", "text", "result", "reply"):
        v = resp_json.get(k)
        if isinstance(v, str):
            return v

    return None


def _clean_and_truncate(text: str, max_chars: int) -> str:
    # Remove HTML tags, excessive whitespace, and truncate with ellipsis
    if not text:
        return ""
    # Remove simple HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Normalize whitespace
    text = " ".join(text.split())
    if max_chars and len(text) > max_chars:
        return text[: max_chars - 1].rsplit(" ", 1)[0] + "…"
    return text


_last_request_time: float = 0.0


def summarize_with_gemini(prompt: str, max_tokens: int = 256) -> str:
    """Call a configured Gemini-compatible HTTP endpoint with retries, backoff and rate limiting.

    Environment variables that influence behavior:
    - GEMINI_ENDPOINT (required)
    - GEMINI_API_KEY (required)
    - GEMINI_MAX_CHARS (optional, default 400)
    - GEMINI_RPM (requests per minute, optional, default 60)
    - GEMINI_MAX_RETRIES (optional, default 3)

    The function will raise if configuration is missing or non-retryable errors occur.
    """
    endpoint = os.environ.get("GEMINI_ENDPOINT")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not endpoint or not api_key:
        raise RuntimeError("GEMINI_ENDPOINT and GEMINI_API_KEY must be set in the environment to use LLM summarization")

    max_chars = int(os.environ.get("GEMINI_MAX_CHARS", "400"))
    rpm = int(os.environ.get("GEMINI_RPM", "60"))
    max_retries = int(os.environ.get("GEMINI_MAX_RETRIES", "3"))

    # Enforce simple rate limit across calls
    global _last_request_time
    min_interval = 60.0 / max(1, rpm)
    now = time.monotonic()
    wait = _last_request_time + min_interval - now
    if wait > 0:
        time.sleep(wait)

    payload = {
        "prompt": prompt,
        "max_output_tokens": max_tokens,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "ai-digest/1.0",
    }

    attempt = 0
    while attempt < max_retries:
        attempt += 1
        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)

            # Update last request time on any attempt that reached the server
            _last_request_time = time.monotonic()

            # Retry on server errors or rate limit responses
            if resp.status_code in (429, 500, 502, 503, 504):
                # Honor Retry-After if provided
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    try:
                        ra = int(retry_after)
                        time.sleep(ra)
                    except Exception:
                        pass
                raise requests.HTTPError(f"Retryable status {resp.status_code}")

            resp.raise_for_status()

            try:
                j = resp.json()
            except Exception:
                text = resp.text.strip()
                return _clean_and_truncate(text, max_chars)

            text = _extract_text_from_response(j)
            if text:
                return _clean_and_truncate(text, max_chars)

            logger.debug("Unexpected LLM response shape: %s", j)
            return _clean_and_truncate(str(j), max_chars)

        except Exception as ex:
            logger.warning("LLM request attempt %d failed: %s", attempt, ex)
            if attempt >= max_retries:
                logger.exception("LLM request failed after %d attempts", attempt)
                raise
            # Exponential backoff with jitter
            backoff = (2 ** (attempt - 1)) + random.uniform(0, 1)
            time.sleep(backoff)
