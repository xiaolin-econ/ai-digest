# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build, Run, and Verification Commands
- Install deps: `pip install -r requirements.txt`
- Collect feed items into SQLite: `python src/collect.py`
- Generate per-item `ai_summary`: `python src/summarize.py`
- Build RSS from DB rows: `python src/build_rss.py`
- Send email digest: `python src/send_email.py`
- Lint: not configured in this repo
- Tests: not configured in this repo
- Single test file: not available (no test runner/tests are defined)
- Single test case: not available (no test runner/tests are defined)

## Environment and Runtime Inputs
- Feed sources are configured in `feeds.yaml`.
- SQLite DB defaults to `data/items.sqlite` via `src/store.py`.
- Optional LLM summary env vars: `USE_GEMINI`, `GEMINI_ENDPOINT`, `GEMINI_API_KEY`, `GEMINI_MAX_CHARS`, `GEMINI_RPM`, `GEMINI_MAX_RETRIES`.
- Email sending requires: `SMTP_HOST`, `SMTP_PORT` (default `587`), `SMTP_USER`, `SMTP_PASS`, optional `DIGEST_TO`.

## High-Level Architecture
- Pipeline: `collect.py` fetches/parses feeds and filters by `KEYWORDS` -> `store.py` upserts `items` rows -> `summarize.py` writes `ai_summary` -> `build_rss.py` renders `rss.xml` -> `send_email.py` renders/sends HTML digest.
- `src/llm.py` is the only LLM integration layer; it handles retries, rate limiting, response-shape extraction, and truncation.
- Data boundary is SQLite (`items` table with `id/source/title/url/published/summary/ai_summary`).
- Automation is in `.github/workflows/collect.yml`, `digest.yml`, and `email.yml`.

## Code Style and Implementation Conventions
- Use 4-space indentation and keep code Python 3.11+ compatible (workflows use both 3.11 and 3.12).
- Prefer stdlib -> third-party -> local import grouping; keep local imports as `from store import ...` / `from llm import ...` within `src/` scripts.
- Follow existing functional script pattern: module-level helpers + `main()` + `if __name__ == "__main__": main()`.
- Keep type hints where practical; strict typing is not enforced.
- Match existing error-handling style: catch exceptions around external I/O (HTTP/SMTP/LLM), log failures, and use graceful fallbacks where available.

## Project-Specific Gotchas
- Run commands from repo root; some paths are resolved from script location (`feeds.yaml`, `data/`), while `build_rss.py` writes `rss.xml` to current working directory.
- `collect.py` filters aggressively by `KEYWORDS`; many feed entries are intentionally dropped.
- `store.connect()` auto-applies schema and backfills missing `ai_summary` column on older DB files.
