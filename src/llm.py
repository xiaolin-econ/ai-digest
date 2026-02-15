import os
import time
import random
import requests
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Default Gemini API endpoint (gemini-2.5-flash)
DEFAULT_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
)


def _extract_text_from_response(resp_json: dict) -> Optional[str]:
    """Extract generated text from Google Gemini generateContent response.

    Expected shape:
    {
      "candidates": [{
        "content": {
          "parts": [{"text": "..."}],
          "role": "model"
        }
      }]
    }
    """
    if not isinstance(resp_json, dict):
        return None

    # Google Gemini generateContent response
    if "candidates" in resp_json and isinstance(resp_json["candidates"], list):
        try:
            first = resp_json["candidates"][0]
            content = first.get("content", {})
            parts = content.get("parts", [])
            if parts and isinstance(parts[0], dict) and "text" in parts[0]:
                return parts[0]["text"]
            # Fallback: content is a plain string (older format)
            if isinstance(content, str):
                return content
        except Exception:
            pass

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


ITEM_PROMPT = (
    "Summarize the following AI research abstract in 2-3 concise sentences. "
    "Focus on the key contribution, method, and result. "
    "Write in plain English accessible to a technical audience.\n\n"
)

DIGEST_PROMPT = (
    "You are given summaries of recent AI research papers. "
    "Write a brief 3-5 sentence overview highlighting the main themes and notable findings. "
    "Do not list individual papers; synthesize the trends.\n\n"
)


def summarize_with_gemini(prompt: str, max_tokens: int = 256, system_prompt: str = "") -> str:
    """Call Google Gemini generateContent API with retries, backoff and rate limiting.

    Environment variables that influence behavior:
    - GEMINI_ENDPOINT (optional, defaults to gemini-2.5-flash generateContent URL)
    - GEMINI_API_KEY (required)
    - GEMINI_MAX_CHARS (optional, default 400)
    - GEMINI_RPM (requests per minute, optional, default 60)
    - GEMINI_MAX_RETRIES (optional, default 3)

    The function will raise if configuration is missing or non-retryable errors occur.
    """
    endpoint = os.environ.get("GEMINI_ENDPOINT", DEFAULT_ENDPOINT)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY must be set in the environment to use LLM summarization")

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

    # Build Google Gemini generateContent payload
    full_prompt = system_prompt + prompt if system_prompt else prompt
    payload = {
        "contents": [
            {
                "parts": [{"text": full_prompt}]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
        },
    }

    # Google Gemini API uses ?key= query parameter for auth
    url = f"{endpoint}?key={api_key}"

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "ai-digest/1.0",
    }

    attempt = 0
    while attempt < max_retries:
        attempt += 1
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)

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
