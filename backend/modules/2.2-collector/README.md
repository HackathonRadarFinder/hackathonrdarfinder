# Module 2.2 – Collector & Compliant Scraping Engine

Collects **raw** web data compliantly and hands it to Module 2.3.

```
sources.json → ToS gate → robots.txt → rate limit → collector (retry) → raw storage + metadata → log
```

Static sources use **Scrapy**; sources that need JavaScript use **Playwright**, and only when the
config says `"type": "dynamic"`. This module does *no* extraction, cleaning or analysis (that is Module 2.3).

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
playwright install chromium       # only needed for dynamic sources
copy .env.example .env            # then set COLLECTOR_USER_AGENT with a real contact
```

## Run

```bash
python run.py                          # all enabled sources in config/sources.json
python run.py --source quotes_static   # one source
python run.py --config other.json
python -m pytest                       # tests (local mock server, no real sites)
python -m pytest --headed              # same, but shows the Chromium window

```

Exit code is 1 only if a source *failed*; `skipped` and `blocked` are normal, compliant outcomes.

## Adding a source (no code changes)

Add an entry to `config/sources.json`:

| field | meaning |
|---|---|
| `source_id` | unique name; letters, digits, `_ - .` (used as folder name) |
| `url` | page to collect (http/https) |
| `type` | `static` (Scrapy, default choice) or `dynamic` (Playwright) |
| `enabled` | `false` to switch off |
| `tos_allows_scraping` | **set `false` if the site's Terms of Service forbid automated access** → source is skipped and logged. Check the ToS before enabling any new source. |
| `tos_note` | why (shown in the skip log) |

Optional for any source: `item_selector` (CSS selector, e.g. `.quote`) - only *counts* matching elements
for the logs/metadata (`item_count`); nothing is extracted. A top-level JSON list is counted automatically.

Extra keys for `dynamic` sources: `wait_for_selector`, `load_more_selector`, `max_load_more` (10),
`scroll_to_end`, `max_scrolls` (10), `action_pause` (seconds, 1.0).

New collector type: subclass `BaseCollector`, call `register_collector("name", Class)`.

## Compliance behaviour

* **robots.txt** is checked by the manager for every source, before any collector runs, so collectors
  cannot skip it. Disallowed → status `skipped`, reason logged, page never requested, no retry.
  Missing robots.txt (404) = allowed. robots.txt returning 401/403/5xx or unreachable = treated as
  *not allowed* (we cannot verify, so we don't scrape). Redirects to another host are re-checked.
* **Rate limit:** random 1–2 s between requests to the same host, strictly sequential (no concurrency).
* **User-Agent & headers:** `COLLECTOR_USER_AGENT` plus honest `Accept`, `Accept-Language` and (if
  `COLLECTOR_CONTACT_EMAIL` is set) a `From:` header, on robots.txt, Scrapy and Playwright requests.
  Never disguised as a browser.
* **ToS:** `tos_allows_scraping: false` → skipped.
* **Blocks:** HTTP 401/403/429 or a CAPTCHA/challenge page → status `blocked`, logged, **never bypassed, never retried**.
  A block also raises an **alert**: a `CRITICAL` log line, a JSON line in `logs/alerts.log`, and (optional) a POST to
  `COLLECTOR_ALERT_WEBHOOK_URL` (Slack-style `{"text": ...}`).
* **Retry:** only temporary failures (timeouts, connection errors, 5xx, 408), max 3 attempts, backoff 2 s then 4 s,
  every retry logged. 404 and other permanent errors are not retried.

## Statuses

| status | meaning |
|---|---|
| `success` | raw content collected and stored |
| `skipped` | robots.txt or ToS said no (nothing scraped) |
| `blocked` | site refused us (401/403/429/CAPTCHA) |
| `failed` | technical failure (retries exhausted, 404, unknown type, …) |

## Handoff to Module 2.3

Only `success` results are stored, under `data/raw/<source_id>/`:

```
data/raw/example_source/20261007T103000Z.html        ← untouched raw content (.json if the response is JSON)
data/raw/example_source/20261007T103000Z.meta.json   ← metadata, points to the raw file
```

Module 2.3 should read records through the storage interface:

```python
from collector_engine.storage.local_storage import LocalRawStorage

storage = LocalRawStorage("data/raw")
for location in storage.list_locations("example_source"):    # or list_locations() for all
    record = storage.load(location)
    html = record["raw_content"]
```

Each `record` is this contract:

```json
{
  "source_id": "example_source",
  "fetched_at": "2026-10-07T10:30:00Z",
  "url": "https://example.com",
  "http_status": 200,
  "raw_content": "<html>...</html>",

  "collector_type": "static",
  "content_type": "text/html; charset=utf-8",
  "content_size": 11064,
  "item_count": 10,
  "final_url": "https://example.com/",
  "attempts": 1
}
```

The first five fields are the guaranteed contract. The rest is optional extra metadata.
`fetched_at` is UTC ISO-8601; `content_size` is bytes (UTF-8). The `.meta.json` file holds the same
fields except `raw_content` (plus `status`, timestamps, robots result, `raw_file`).

### S3 storage

Set in `.env` (credentials come from the normal AWS mechanisms: env vars, `~/.aws`, IAM role):

```
COLLECTOR_STORAGE=s3
COLLECTOR_S3_BUCKET=my-bucket
COLLECTOR_S3_PREFIX=raw/
```

Same layout as local (`raw/<source_id>/<stamp>.html` + `.meta.json`) and the same `load()` / `list_locations()` API,
so Module 2.3 code works unchanged. For another backend (raw DB, etc.) implement `RawStorage` (`storage/base.py`).

## Logging

Standard `logging`, console + `logs/collector.log` (rotating). Per source: `JOB_START`, then one `JOB_END`
line with `source_id, url, collector, status, start, end, robots, http_status, content_size, items, attempts, reason`.
Retries (`retry ... attempt=1/3 ...`), `SKIPPED`, `BLOCKED` and `FAILED` events get their own lines; `RUN_END` summarises.

## Layout

```
config/sources.json            source list
src/collector_engine/
  models.py                    Source, CollectionResult (handoff contract), exceptions
  config/loader.py             sources.json + .env settings
  collectors/                  base_collector, static_collector (Scrapy), dynamic_collector (Playwright), registry
  compliance/                  robots_checker, rate_limiter, tos_checker
  retry.py                     retry with exponential backoff
  storage/                     RawStorage interface, LocalRawStorage, S3RawStorage, factory
  monitoring/                  logger.py, alerts.py (block alerts)
  items.py                     item counting for logs (no extraction)
  manager.py                   the pipeline (all compliance steps live here)
  main.py                      CLI
tests/                         pytest suite with a local mock website
```

## Known limitations

* One page per source (no crawling or pagination across URLs).
* Playwright's sub-requests (scripts, images, XHR made by the page) are not individually robots-checked or rate limited; only the page URL is.
* S3 storage is tested with an in-memory fake client only; verify once against your real bucket.
* ToS compliance is a human-set flag; it cannot be detected automatically.
* No proxy use, no CAPTCHA solving, no login support, by design.
* Scrapy runs in a subprocess per fetch (≈1–2 s start-up) because its reactor can't be restarted in-process.
