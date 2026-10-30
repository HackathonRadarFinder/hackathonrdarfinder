# First real-data pilot acceptance — 25 October 2026

The first reviewed real record passed disposable database → FastAPI → existing
React EventCard acceptance before the 28 October target. This is a one-record
acceptance, not a claim that the full 25-record pilot or 206-record catalog is
approved. The main 206-row source/review exports have not been changed.

## Pilot and evidence

- Selected 25 distinct candidates: 24 Unstop rows with supplied organizer,
  location, prize and deadlines on/after 28 October, plus Hacknauts on Devfolio
  whose missing organizer was resolved from its original public page.
- Explicit, fact-based approvals: 1. Pending: 24. Schema validation does not
  approve any row. Without review_decisions.json decisions the worker emits zero
  approvals, even though candidates are well formed.
- Reviewer: Codex, AI assistant, acting on this session's explicit user request.
  No human reviewer identity or human approval is claimed.
- selection.json and pilot_candidates.csv contain the pilot; reviewed.csv contains
  only the single explicitly reviewed record. The decisions ledger is retained
  separately. evidence_checklist.json/.md contain individual field status and
  verified values for every selected record. Unverifiable values are null there;
  the raw provider claims remain separate for further review.
- Remaining records were not fully verified. Several Unstop URLs returned no
  extractable text or were unavailable through the research tool. Unchecked URLs
  are explicitly marked not individually checked following these failures;
  no CAPTCHA, authentication or private-endpoint workaround was attempted.

Original-page verification: https://hacknauts26.devfolio.co/
The page identifies Causmic Club, the Ludhiana college venue, in-person mode and
November 14–15 calendar dates. Exact event times were not established. The API's
application deadline was not independently established; a date labelled as PPT
submission is not reused as registration. The approved record therefore leaves
registration_deadline and prize blank, keeps day precision with a midnight-storage
caveat, and retains the original raw API values in provenance. A displayed mixed
sponsor award figure is not asserted to be a cash prize total.

Conflict retained, not approved:
https://unstop.com/hackathons/wcc-forge-48-wecodecoders-1756040/amp
This publicly indexed event page was readable, but its sections disagree on
registration timing and the start hour. Search-index snippets or an API-host alias
are not treated as full verification of other original event URLs.

API reuse basis checked: https://brabble.ai/docs
Brabble permits reuse with visible credit/link; existing attribution is preserved.
This is not permission to run direct Unstop/Devfolio scrapers. Their approvals.json
flags remain false. Original HTTP API envelopes were unavailable in the supplied
snapshot; canonical API-record checksums are not HTML or transport proofs.

## Dry-run and disposable acceptance results

- pilot_candidates.csv: approved_and_valid=1, not_approved=24, applied=false.
- reviewed.csv: approved_and_valid=1, not_approved=0, applied=false.
- In an empty disposable SQLite database, importer staging would insert 1 and
  skip 0 duplicate URLs. Dry-run rollback leaves zero events.
- Actual disposable commit: inserted=1, duplicate_urls=0.
- Repeat import: inserted=0, duplicate_urls=1.
- GET /events/, page_size=1 pagination (including an empty second page), and
  GET /events/{id}: passed. Required API attribution and null unknowns survived.
- The temporary database was deleted afterward. API responses and machine-readable
  acceptance results are retained under acceptance/ for inspection.
- Frontend integration creates another temporary database, loads this reviewed
  real CSV through the importer, retrieves the API response, and renders the actual
  React card through the existing API client. Brabble link, factual title/organizer,
  day-precision caveat and unknown application deadline are asserted.
- Full headless Chromium acceptance also passed over real loopback HTTP: temporary SQLite ? FastAPI ? Vite proxy ? React catalog, pagination and event detail. External browser requests were blocked. There were zero browser page errors; fixture exit code was 0 and temporary database cleanup was confirmed. Screenshots and report are under .test-support/brabble-pilot-browser/.
- Backend affected suite: 276 passed, one existing Starlette deprecation warning.
- Frontend suite: 18 passed, one pre-existing optional external-backend smoke test
  skipped because its separate disposable server was not configured.

## Configured development database — not connected

Redacted configuration: ENVIRONMENT=development, postgresql+psycopg, host=db,
database=hackathon_radar. docker-compose.yml describes this as the local development
PostgreSQL service with a loopback-only host port. No credentials are in this report.
Configuration matches the development profile, but server identity and existing
rows could not be checked: the configured Docker Linux daemon pipe is unavailable.
No development/production DB connection, import, container startup or deployment
was performed. Exact duplicate counts against that existing database remain unknown;
the insert/skip counts above are for disposable acceptance only.

The importer now requires --expect-database for --apply and refuses production,
remote or ambiguous configurations. Review flags alone no longer suffice: each
approved API row needs reviewer identity/type, timestamp, permission basis,
per-field checks, date precision and a hash binding the reviewed EventCreate values.
Changed facts/precision and unresolved conflicts require re-review. Synthetic test
attestations are explicitly refused by CLI apply.

An image packaging gap was also corrected: Dockerfile previously omitted the
radar_collector Python module/dependencies needed by the reviewed importer. It now
copies only that code and installs its existing requirements; snapshot outputs
are excluded from the build context. No image build was possible without Docker,
and none was attempted. A future controlled container import requires an operator
reviewed image built from this updated worktree; do not use a stale image.

## Exact local verification commands

From .release-local/backend:

```powershell
$env:DEBUG = 'false'
.\.venv\Scripts\python.exe -m workers.prepare_brabble_pilot
.\.venv\Scripts\python.exe -m workers.import_reviewed_public radar_collector/output/brabble-pilot/reviewed.csv --check-target --expect-database hackathon_radar
.\.venv\Scripts\python.exe -m workers.import_reviewed_public radar_collector/output/brabble-pilot/pilot_candidates.csv
.\.venv\Scripts\python.exe -m workers.import_reviewed_public radar_collector/output/brabble-pilot/reviewed.csv
.\.venv\Scripts\python.exe -m workers.accept_brabble_pilot
.\.venv\Scripts\python.exe -m pytest tests/test_brabble_pilot.py tests/test_brabble_ingestion.py tests/test_brabble_refresh.py tests/test_reviewed_public_import.py tests/test_scraper_ingestion.py tests/test_discovery.py tests/test_discovery_history.py tests/test_event_pagination.py tests/test_events_services.py tests/test_account_integration.py radar_collector/tests -q
```

From .release-local/frontend:

```powershell
npm test
node tests/pilot.browser.mjs
```

## Final controlled development import — currently blocked, not executed

First restore the local Docker daemon, confirm the active context is local, and
independently verify the running db service is this development stack. Confirm
its current database/migration state. Re-review dynamic facts if the snapshot is
stale. Review the worktree changes and arrange an updated development backend image
through the normal operator workflow; this task did not build or deploy one.

Once those prerequisites are satisfied, run from the .release-local root:

```powershell
# Read-only identity checks; no database password is printed.
docker context show
docker compose exec -T db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT current_database();"'
docker compose exec -T backend alembic current
# The image intentionally does not bundle raw snapshots or reviewed CSV files.
docker compose cp backend/radar_collector/output/brabble-pilot/reviewed.csv backend:/tmp/reviewed-brabble-pilot.csv
docker compose exec -T backend python -m workers.import_reviewed_public /tmp/reviewed-brabble-pilot.csv --check-target --expect-database hackathon_radar
docker compose exec -T backend python -m workers.import_reviewed_public /tmp/reviewed-brabble-pilot.csv
# Only after confirming that target and the real review, substitute your actual operator identifier:
docker compose exec -T backend python -m workers.import_reviewed_public /tmp/reviewed-brabble-pilot.csv --apply --reviewed-by YOUR_OPERATOR_ID --expect-database hackathon_radar
```

Do not use the 206-row queue as an approved catalog. Do not approve the remaining
24 from schema validity, search snippets or unreadable pages. No production
scheduler/source was enabled; no commit, push, merge or deployment was performed.
