# India institution discovery: operating guide

Implemented on `feature/india-wide-discovery`, based on develop
`c71df5672626cb0bcb27a86a24f2e2da95a696a5` in `.india-discovery`.
Read [the pre-implementation audit](INDIA-DISCOVERY-ROOT-CAUSE.md) first.

## Permission and real coverage

No bulk directory permission, licensed export or approved live pilot source was
provided during implementation. **Zero new real institutions, approved real
sources or live-discovered hackathons are claimed.** The existing five reviewed
catalog records are preserved; three historical Megathon facts are used in
extraction regression, not counted as new discoveries. Synthetic offline pilots
cover Telangana, Tamil Nadu, Maharashtra and Assam; these are test fixtures only.

AISHE/UGC are preferred provenance providers, not implicitly approved crawls.
AISHE's [website policy](https://aishe.gov.in/website-policies/) requires permission
for reuse beyond download. Obtain an approved export or an applicable open-data
license before import, and separate terms/source approval before live collection.
Public accessibility and robots permission do not establish reuse rights.
The importer records an operator's attestation; it cannot independently establish
legal permission or verify a website's ownership from the supplied text.

## Directory import

New Alembic head: `e0f1a2b3c4d5`. Apply migrations only to an explicitly selected
disposable/pilot database for initial validation. Never use the preserved
`verify_local.db` for tests. Production migration requires separate approval and
backup/restore evidence. The migration adds two tables (`institutions`,
`discovery_announcements`) and nullable event geography/registration/eligibility
columns; existing rows remain valid.

From `backend`, using the verified project Python interpreter:

```powershell
python -B -m workers.import_institutions --input <approved-export.json> --validate-only
python -B -m workers.import_institutions --input <approved-export.json>
```

JSON is a `DirectoryImport` envelope:

- `provider`: `aishe`, `ugc` or `institution`.
- `source_url`: actual HTTPS official provenance; AISHE/UGC providers restrict
  provenance to their official domains or `data.gov.in` and subdomains.
- `reuse_permitted`: explicit boolean true, plus actual `license_reference` and
  `reviewed_by` (nonblank); do not fill these with an assumed permission.
- `records`: up to 5000 institution records per batch; file maximum 10 MB.

Each record requires `identifier`, `name`, `state`, `category`, and timezone-aware
`verified_at` no later than now. Preserve official identifiers under namespaces
`AISHE:<original-code>`, `UGC:<original-code>`. `OFFICIAL:<operator-local-id>` is
explicitly a local identifier and must not be presented as an AISHE/UGC code.
District/city are nullable, not guessed. Optional website requires an official
`website_evidence_url` and nonfuture `website_verified_at`. `event_urls` is an
explicitly reviewed list of HTTPS URLs on that same verified website origin;
do not synthesize `/events` URLs. External organizer domains need their own
reviewed source entry; automatic affiliation inference is not implemented.

CSV imports accept an explicit canonical-field-to-CSV-column JSON map and a JSON
permission envelope without records. No column semantics are guessed:

```powershell
python -B -m workers.import_institutions --input <approved-export.csv> --metadata <permission.json> --columns <column-map.json> --verified-at <reviewed-UTC-timestamp> --validate-only
```

`--verified-at` supplies an operator review timestamp if the CSV lacks one.
Unprefixed official codes receive the provider namespace; no new government code
is generated. Website verification columns must be supplied explicitly or left
unset. Approved imports are also available through the audited source-manager
endpoint `PUT /admin/discovery/institutions`.

Imports upsert by identifier atomically. Identical rows are unchanged; older
verification timestamps are skipped; conflicting changes at the same timestamp
are rejected. Changed directory facts disable linked sources for re-review.
The directory's stored permission status records a decision; the source policy's
enabled/review/expiry/terms checks remain authoritative at execution time.

## Register and schedule sources

Existing protected `PUT /admin/discovery/sources` accepts these adapters:

| Adapter | Input / behavior |
|---|---|
| `official-html-v1` | Static college, technical-festival, innovation-cell or organizer HTML; JSON-LD Event extraction, otherwise flagged text candidate |
| `rss-v1` | Public RSS or Atom announcements, preserving item links; never guesses dates from publication timestamps |
| `sitemap-v1` | Sitemap hackathon links staged for review; does not follow links or nested indexes automatically |
| `events-json-v1` | Authorized `{"events":[...]}` feed, or schema.org Event/graph JSON; fields use schema.org names such as `name`, `startDate`, `url`, `organizer` |
| `curated-v1`, `unstop-v1` | Existing reviewed manifest and governed Unstop behavior retained |

New college-page sources require `institution_id`; every source associated with
an institution must match one of its explicitly verified `event_urls`. General
authorized feeds may omit institution affiliation. An unsupported platform's
proprietary API needs a tested normalization adapter; it is not silently treated
as the documented JSON feed contract.

A policy contains `key`, `name`, `adapter`, HTTPS `url`, `owner`, actual permission
`basis` and `reference`, timezone-aware `reviewed_at`/`expires_at`,
`terms_permit=true`, `enabled=true`, and `interval_seconds` (300–604800). Never set
these approval fields just to make a source run. Registration starts no network
access. A changed policy becomes due for the next worker pass, not an immediate
collection during the API request.

After approval, with the isolated pilot `DATABASE_URL`, real collector contact
identity and application secret configured securely in the worker environment:

```powershell
$env:DISCOVERY_ENABLED='true'
python -B -m workers.discovery --allow-live --batch-size 5
python -B -m workers.discovery --allow-live --batch-size 5 --watch --poll-seconds 30
```

Start with one worker and measured batches. Concurrency is deliberately bounded
at **one**, preserving the existing durable global writer lock. Batch size is
1–100 (default 10). Do not run legacy/manual ingestion writers concurrently.
This is not a claim of distributed nationwide throughput. A crashed writer's
durable lock still requires operator reconciliation; never delete an active lock.

New adapters reuse `CollectorManager`, its pinned-address SSRF protections,
explicit origin scope, redirect/DNS checks, robots, timeout/response bounds,
per-domain delays and transient-error backoff. A shared worker manager preserves
domain rate-limit state across sources. A bounded in-memory cache retains up to
16 documents for 300 seconds; policy gates still precede every scheduled run.
Raw documents remain in the governed collector's configured local storage; keep
them outside Git. The new adapters limit content to 2 MB and batches to 1000
announcements. XML parsing rejects entities/external resources. Known URL tracking
parameters are removed; identity-bearing query parameters are retained.

There is no CAPTCHA/login/bot-protection bypass. Dynamic browser collection is
not enabled. JavaScript-only pages require a separately implemented/reviewed
rendering adapter or an approved static feed; the system does not claim those
pages are covered. No optional AI service is called.

## Review and publish

All new adapter output is staged in `discovery_announcements`, absent from public
event search and predictions. Extraction preserves title, organizer, location,
state, mode, registration URL/deadline, start/end, eligibility and prize **only
where present**, plus source URL, observation, content checksum, issues and raw
date evidence. Unstructured pages and sitemap links are explicitly uncertain.

Date-only source values remain in `evidence.raw_dates` with a day-precision issue;
they do not invent a timestamp. The current new-publication path requires a
reviewed offset-bearing start timestamp. Date-only announcements therefore stay
pending until adequate evidence is available; do not invent a start time to
approve one. This conservative limitation should be addressed with a dedicated
date-precision schema before broad date-only publishing.

Database-backed `reviewer` or `administrator` roles can list the queue:
`GET /admin/discovery/announcements?status=pending&page=1` (50 per page), and submit
`POST /admin/discovery/announcements/{id}/review` with:

```json
{"decision":"approved","note":"Actual factual review basis, including corrections","event":{"title":"...","organization":"...","url":"<observed URL>","institution_id":123,"state":"<verified state>","start_date":"<verified ISO timestamp with timezone>"}}
```

This is a contract illustration, not an importable fact or approval. Copy actual
candidate facts and fill only source-supported values. `rejected` needs a note
and no event. Source managers manage source policy; that role alone does not
authorize factual publication. All decisions are audited.

Approval preserves observed URL/institution/source/timestamp. It refuses expired,
disabled or reconfigured sources, already-reviewed candidates, newer observations
of the same URL, conflicting event ownership, and an occupied writer lock.
Publication reuses existing deduplication, event versions and discovery evidence
atomically. Unchanged repeated observations update last-seen and duplicate
counters; changed facts create another pending revision. There is no fabricated
historical edition, automatic fuzzy cross-source merge or prediction promotion.

## Frontend and monitoring

Explore supports exact case-insensitive state filtering and institution ID
filtering alongside existing filters. Institution name search and state narrow a
bounded directory selector; its first 100 results are disclosed. Public API:
`GET /institutions?q=<name>&state=<state>&page=1&page_size=100` and
`GET /events/?state=<state>&institution_id=<id>`. Registration/eligibility fields
appear in reviewed event detail when available.

Administration displays coverage counts and recent source-key/status/error runs.
Source managers/admins can read `/admin/discovery/coverage`. Metrics distinguish
institutions, verified websites, currently approved sources, institutions with
approved sources, distinct checked live-source entries, discovered announcement
revisions, approved revisions, pending/rejected reviews, duplicate observations,
failures, awaiting-permission sources and last successful run. They do not claim
all institutions have hackathons. Revision counts are not unique current-event
counts. Metrics currently aggregate stored runs at request time; materialized
daily aggregates/retention are a future requirement at substantial run volume.

## Local verification commands

The test URL helpers permit only unprivileged loopback HTTP URLs without
credentials/query/fragment; each suite still verifies its exact disposable marker
before writes. Original 5174/5176 defaults remain usable. Separate worktrees may
use 5184/5186 with backends 8024/8026:

```powershell
python -B scripts/disposable_backend.py --port 8024
python -B scripts/local_demo.py --port 8026 --discovery
# Separate frontend terminals, using VITE_API_BASE_URL=/api:
# API_PROXY_TARGET=http://127.0.0.1:8024 npm run dev -- --port 5184 --strictPort
# API_PROXY_TARGET=http://127.0.0.1:8026 npm run dev -- --port 5186 --strictPort
```

From frontend, run general acceptance before the new pilot suite (the latter
adds synthetic directory facts and associates one fixture event):

```powershell
$env:FRONTEND_DISPOSABLE_API='http://127.0.0.1:5184/api'
npm test
$env:FRONTEND_DISPOSABLE_BROWSER_BASE='http://127.0.0.1:5184'
npm run test:browser
npm run test:india
$env:FRONTEND_CURATED_DEMO_BASE='http://127.0.0.1:5186'
$env:FRONTEND_DISCOVERY_EXPECTED='true'
npm run test:curated
npm run lint
npm run build
```

Python regression roots remain `backend/tests`,
`backend/modules/2.2-collector` (from its own directory), and `tests/operations`.
Do not collect independently named prototype `app` packages together from the
backend root. Browser evidence stays in ignored `.test-support/`; no generated
database, raw scrape, credential or evidence artifact should be committed.

## Next approval-dependent step

Supply an authorized AISHE/UGC export or verified institution data with its reuse
license, and a diverse pilot list with actual website/event URL evidence, source
permission basis, reviewer and expiry. Validate/import in a new isolated pilot
database, register only those approved sources, collect one bounded batch, review
real announcements and compare source facts before expansion. No live pilot,
push, public deployment, SMTP or external paid service was enabled here.
