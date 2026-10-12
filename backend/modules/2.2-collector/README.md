# Module 2.2: governed raw collection

Static collection uses the bounded HTTP transport in `network.py`. It returns raw
HTML or JSON for offline normalization. Dynamic collection is disabled and raises
`BlockedError` before any browser import or network request. Scrapy and Playwright
are no longer used or required. CSS monitoring counts use Parsel directly; invalid
selectors return an unknown count without failing collection.

## Setup and validation

From the repository root, use the existing project virtual environment:

```powershell
backend/.venv/Scripts/python.exe -m pip install -r backend/modules/2.2-collector/requirements.txt
backend/.venv/Scripts/python.exe -m pytest -c backend/modules/2.2-collector/pytest.ini backend/modules/2.2-collector/tests -q
cd backend
.venv/Scripts/python.exe -m pytest tests -q
```

Collector tests use a local fixture server and enforce loopback-only connections.
Production transport forbids loopback; tests explicitly inject `URLPolicy(...,
allow_loopback=True)`. There is no environment setting that enables local access.
Backend ingestion tests use disposable SQLite databases, never the development DB.

To run collection, change into `backend/modules/2.2-collector`, configure identifying
headers using `.env.example`, and run `python run.py --source SOURCE_ID`. This performs
network requests only for sources whose permission is explicitly enabled. Example
sources are unapproved by default and are skipped until a human records permission.
Do not enable them just to run tests.

## Source configuration

`sources.json` contains a `sources` list. Each source requires a safe unique
`source_id`, an HTTP(S) `url`, and `type` (`static` or disabled `dynamic`). `enabled`
defaults to true. `tos_allows_scraping` defaults to **false**; only JSON boolean true
records explicit scraping permission. Strings such as `"false"`, integers and null
are rejected. `tos_note` records the permission decision. Additional keys or an
`options` object are collector options; `item_selector` counts CSS matches for
monitoring and does not extract data. Dynamic options have no operational effect.

## Request governance

The manager applies the permission gate before network access. Robots rules are
checked before the initial content request and every redirected request, including
same-origin path changes. Disallowed requests are skipped and never fetched.
Only robots HTTP 404/410 mean no policy is published; restricted, throttled,
unexpected or unverifiable responses fail closed. Rules are cached per origin.
Robots redirects must remain on that origin's `/robots.txt` resource; redirects to
content paths are refused before fetching them.

Production permits only the configured source origin. Cross-origin redirects are
refused; specialized callers may inject an explicit origin policy. Every DNS answer
must be globally routable, and the connection uses a validated numeric address
without a second lookup. HTTPS uses certificate verification and hostname checks.
Credentials in URLs, private/reserved destinations, sensitive request headers,
cookies, proxies and compressed responses are not supported.

The transport enforces timeout, response byte, redirect and elapsed-time limits.
The manager shares one elapsed-time budget across robots, content and retries.
Rate limiting applies before every request, including robots, redirects and retries.
Requests identify the collector with `COLLECTOR_USER_AGENT` and optional
`COLLECTOR_CONTACT_EMAIL` (`From`). Set a real contact before approved collection.

| Environment field | Default | Valid range |
|---|---|---|
| `COLLECTOR_REQUEST_TIMEOUT` | 30 seconds | >0 to 120 |
| `COLLECTOR_MAX_RESPONSE_BYTES` | 2,000,000 | 1 to 10,000,000 |
| `COLLECTOR_MAX_REDIRECTS` | 5 | 0 to 10 |
| `COLLECTOR_MAX_JOB_SECONDS` | 120 seconds | >0 to 600 |
| `COLLECTOR_MIN_DELAY`, `COLLECTOR_MAX_DELAY` | 1, 2 seconds | finite, 0 to 600; min <= max |
| `COLLECTOR_MAX_ATTEMPTS` | 3 | 1 to 10 |
| `COLLECTOR_BACKOFF_BASE`, `COLLECTOR_BACKOFF_FACTOR` | 2, 2 | finite; base 0 to 600, factor 1 to 600 |

HTTP 401/403/429 and CAPTCHA/challenge pages are `blocked` and never retried or
bypassed. Only temporary failures (connection errors, timeouts, 408, 5xx) retry with
exponential backoff. Permanent failures are `failed`. Permission or robots refusal
is `skipped`. Disabled dynamic collection is `blocked` without network activity.
Unknown collector types fail before requests. CLI exit code is 1 for failed jobs,
2 for invalid configuration, otherwise 0.

## Storage, monitoring and backend handoff

Only successful collections are stored. Local storage uses contained source folders
and unique timestamped raw `.html`/`.json` files, then atomically publishes metadata.
`LocalRawStorage.load(location)` returns `source_id`, `fetched_at`, `url`,
`http_status`, `raw_content`, plus final URL, content type/size, item count and attempts.
`fetched_at` is UTC ISO-8601. `content_size` measures UTF-8 bytes of decoded content;
the transport limit measures received bytes. Raw content is never added to logs.

`COLLECTOR_STORAGE=s3` selects S3 with `COLLECTOR_S3_BUCKET` and `COLLECTOR_S3_PREFIX`;
credentials use normal AWS configuration. Tests use an in-memory fake S3 client.
Logs contain job outcomes and retries; blocks also produce an alert file and an
optional explicitly configured webhook (`COLLECTOR_ALERT_WEBHOOK_URL`).

The FastAPI backend adapter `app.services.scraper_ingestion` exposes
`normalize_unstop_collection(record)` and `ingest_events(session, events)`. The former
validates a successful HTTPS Unstop API envelope, normalizes opportunities offline,
and counts rejected items. The latter validates all inputs before writes, creates
organizations, skips duplicate source/URL pairs, and stages a batch in a SAVEPOINT.
It never opens a database or commits. The caller decides commit or rollback; SQLite
gets an explicit outer transaction so SAVEPOINT release cannot silently commit.
A database failure rolls back the batch, preserving already-flushed caller work.
Pending caller changes are rejected to avoid an implicit flush.

The old standalone Unstop `scrape()` entry point is retired and refuses before
network access. Its `normalise()` helper remains available for offline input.

## Limitations

One page per source; no crawling or automatic pagination. Dynamic collection remains
disabled until all browser requests can obey the same policy. Permission is a human
recorded decision. Use a single ingestion writer per source: the existing database
has no source/URL uniqueness constraint, so concurrent duplicate insertion needs a
separate schema migration. Curated rows are never overwritten. Real S3 operation
has not been exercised by the offline tests.
