# ai-digest

Automated AI research digest pipeline:
- Collects feed entries from `feeds.yaml`
- Filters for productivity/agent-related papers
- Stores items in SQLite (`data/items.sqlite`)
- Generates short summaries (local or Gemini endpoint)
- Builds `rss.xml` and can email a digest

## Requirements
- Python 3.11+ (CI uses 3.11 and 3.12)
- Install dependencies:

```bash
pip install -r requirements.txt
```

## Local Run Commands
Run from repo root:

```bash
python src/collect.py
python src/summarize.py
python src/build_rss.py
python src/send_email.py
```

## Environment Variables
- Summarization (optional LLM): `USE_GEMINI`, `GEMINI_ENDPOINT`, `GEMINI_API_KEY`, `GEMINI_MAX_CHARS`, `GEMINI_RPM`, `GEMINI_MAX_RETRIES`
- Email (required for `send_email.py`): `SMTP_HOST`, `SMTP_PORT` (default `587`), `SMTP_USER`, `SMTP_PASS`
- Optional email recipient override: `DIGEST_TO` (defaults to `SMTP_USER`)

## GitHub Actions Schedules
- `.github/workflows/collect.yml`: currently manual-only (`workflow_dispatch`); automatic weekly RSS rebuild is paused
- `.github/workflows/digest.yml`: currently manual-only (`workflow_dispatch`); automatic weekly digest email is paused
- `.github/workflows/email.yml`: manual-only (`workflow_dispatch`) email send helper

## Paused Automation Note
Weekly GitHub Actions automation is currently paused for both RSS generation and digest email delivery.

To resume it later, restore the `schedule` blocks in these workflow files:
- `.github/workflows/collect.yml`: re-add `cron: "0 6 * * 1"` to resume weekly collect + RSS build
- `.github/workflows/digest.yml`: re-add `cron: '0 7 * * 1'` to resume weekly digest generation + email send

Manual runs are still available from the GitHub Actions tab through `workflow_dispatch`.
