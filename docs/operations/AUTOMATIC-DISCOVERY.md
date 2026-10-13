# Automatic discovery and prediction-history handover

Baseline MVP: `0f9f56a` (`feat(mvp): add isolated curated demo and date filters`).
The seven authorized files were committed and the release worktree was clean
before creating `feature/automatic-discovery`. Feature work remains uncommitted.
This is a local demonstration and research pipeline, not a public release.

## Run the isolated discovery demo

PowerShell terminal 1:

```powershell
Set-Location 'C:\Users\nakul\OneDrive\Documents\Desktop\hackathonradarfinder\.release-local'
$env:PYTHONDONTWRITEBYTECODE = '1'
& '..\backend\.venv\Scripts\python.exe' -B scripts/local_demo.py --discovery
```

Terminal 2:

```powershell
Set-Location 'C:\Users\nakul\OneDrive\Documents\Desktop\hackathonradarfinder\.release-local\frontend'
$env:API_PROXY_TARGET = 'http://127.0.0.1:8021'
npm.cmd run dev -- --configLoader native --port 5176 --strictPort
```

Frontend: http://127.0.0.1:5176. Backend: http://127.0.0.1:8021.
API documentation: http://127.0.0.1:8021/docs. Health: `/health`.
Stop Vite with Ctrl+C in its terminal, then stop the launcher with Ctrl+C.
The launcher also terminates its own scheduler, closes connections and removes
its temporary SQLite database. Stop only these project processes.

The launcher applies migrations in a fresh temporary database, registers the
existing reviewed five-event snapshot, collects it twice to verify idempotence,
and starts the scheduler. The second verification run is explicitly made due;
observation timestamps are not advanced into the future. Subsequent collection
is due every six hours; the worker checks every 30 seconds. Email is disabled.
The original launcher without `--discovery` still supports the MVP demo.

Demonstrate Explore, search/location/mode/UTC date filters, an event's discovery
and update history, registration/login, save/unsave, consent/preferences, stored
notifications, logout and denial of ordinary-user admin access. Public prediction
and password recovery states remain accurately unavailable.

Dependencies: existing repository-root Python 3.12.6 environment
`backend/.venv/Scripts/python.exe`, backend requirements, Node 24.19.0,
frontend node_modules, and Chrome/Edge for browser tests. No global installation,
Docker, SMTP or PostgreSQL is needed for this demo.

## Architecture and source controls

- SQLAlchemy registry extends existing `sources`; source management uses actual
  database roles (`administrator` or `source_manager`) and writes audit logs.
  `PUT /admin/discovery/sources` registers policy without starting network access.
  GET on the same path lists policies; `/admin/discovery/runs` lists run outcomes.
- Supported adapters: fixed reviewed `curated-v1` offline snapshot and `unstop-v1`
  using the existing CollectorManager, governed HTTP transport, robots checks,
  retries, bounded transfer and raw storage. Unstop integration was tested with
  mocked collection results. No live permission has been invented or activated.
- Policy includes enabled state, interval (300–604800 seconds), owner, permission
  basis/reference and timezone-aware review/expiry. Live collection additionally
  requires explicit terms permission and the worker's `--allow-live` flag.
  Expired/future approval or missing terms pauses and disables the source.
- The explicit worker is inert unless `DISCOVERY_ENABLED=true`. For an already
  configured **disposable** database, run from backend with its isolated
  DATABASE_URL/SECRET_KEY: `python -B -m workers.discovery --watch`.
  `--poll-seconds` accepts 5–60; omit `--watch` for one due collection pass.
  Do not use `--allow-live` until actual source approval is recorded and reviewed.
- Full batches are validated before writes. Each source/URL identity maps to one
  event. Same-source material changes create immutable EventVersion snapshots;
  unchanged observations append evidence without duplicate versions. Older
  scraped records and cross-source ownership conflicts do not overwrite events.
- Each observation retains source, raw-document checksum, adapter version and
  snapshot. Run metrics include insert/update/unchanged/rejected/conflict counts.
  `/events/{id}/discovery` exposes bounded public evidence/version history; React
  lists discovered events through the existing event API and displays provenance.
- A durable database singleton lock serializes discovery writers. Event writes,
  versions, evidence and successful completion commit atomically. Invalid batches
  roll back; error codes do not expose raw content or SQL credentials. Existing
  legacy ingestion/admin writers must not run concurrently with discovery.

## Troubleshooting and limitations

Source not running: check worker opt-in, enabled state, next_run_at and approval
expiry, then protected run logs. `not_due` is expected between scheduled runs.
`live_collection_disabled` is expected without explicit live opt-in. Permission,
robots denial or transport failure must not be bypassed.

A crashed worker can leave a durable lock and a `running` run. There is deliberately
no timed takeover that could allow two writers. Stop all discovery workers, verify
the recorded run has no active owner, and reconcile the interrupted run/lock in
the disposable database before restarting. Restarting the demo is the simplest
safe reset. Never delete a lock while its worker is active.

Port in use: stop only the known demo terminal/process; do not broadly kill Python
or Node processes. Backend import errors: use the explicit verified Python path.
Frontend API failures: check `/health` on 8021 and restart Vite with the documented
proxy environment variable. No existing databases are modified by the launcher.

Only two source adapters are implemented. Unstop fetches one configured search
page per run; configure separately approved page URLs if needed. No exhaustive
coverage or cross-source fuzzy identity matching is claimed. PostgreSQL execution
was not verified in this phase because the local Docker daemon is unavailable;
all integrations use disposable SQLite and migration/schema checks.

## Historical data preparation

`ai.discovery_history` exports event observations and provenance without account
data. `as_of` selects only versions known at a cutoff. Temporal baseline evaluation
requires an explicit reviewed event-ID-to-edition-family map; organizer similarity
does not establish a recurrence family. Features exclude the target edition and
future event dates. Labels are source-announced dates, not confirmed actual dates.

From backend with an explicitly configured disposable database:

```powershell
python -B -m workers.prepare_prediction_history --output "$env:TEMP\radar-history-new.json" --evaluation-as-of '2026-10-13T23:00:00' --cutoff '2025-01-01T00:00:00'
```

Use the verified interpreter rather than an unverified shell Python. Timestamps
are UTC-naive, matching stored evidence. `--families` accepts the reviewed JSON
map; repeat `--cutoff` for temporal folds. Output must be a new filename. Export
is read-only and bounded by evaluation observation time. Without sufficient
families/history the report is `insufficient_history`, zero folds and null MAE.

The five current records cannot substantiate calibrated predictions. Synthetic
fixtures verify cutoff exclusion and baseline arithmetic only. More approved
historical observations, reviewed edition identities, actual outcome labels,
temporal evaluation/calibration and publication approval are required before any
public forecast. No prediction publication control was enabled.

## Verification evidence

October 13, 2026: disposable migrations and repeat ingestion succeeded (five
events, five unchanged on repeat); backend health and frontend proxy worked.
Backend/operations regression: **416 passed**. Final affected discovery/history
checks: **13 passed**. Collector: **157 passed**. Frontend tests: **16 passed**
(no skips). Browser regression: **30 checks and 22 axe scans passed**. Curated
discovery journey: **13 checks passed**. Frontend lint/build and git diff checks
passed. The existing Starlette/httpx deprecation warning remains nonblocking.
Focused tests cover scheduling opt-in, expired/missing permissions, locked writer,
invalid-batch rollback, stale updates, version history, role denial/audited registry,
mocked Unstop handoff, temporal leakage prevention and read-only export.

No push, merge, deployment, global dependency change or live scraping was performed.
Review feature diff and approve a separate feature commit before finalization.

## Feature file inventory

Changed existing files:

```text
backend/app/main.py
backend/app/models/__init__.py
backend/app/models/core.py
backend/app/services/event_service.py
backend/tests/test_auth_revocation.py
docs/operations/LOCAL-MVP-20261014.md
frontend/src/LivePlatform.jsx
frontend/src/services/apiClient.js
frontend/tests/curated.acceptance.mjs
scripts/disposable_pg_mvp.py
scripts/local_demo.py
```

New files:

```text
backend/ai/discovery_history.py
backend/app/api/routes/discovery.py
backend/app/models/discovery.py
backend/app/schemas/discovery.py
backend/app/services/discovery_service.py
backend/database/migrations/versions/d9e0f1a2b3c4_discovery_pipeline.py
backend/tests/test_discovery.py
backend/tests/test_discovery_history.py
backend/workers/discovery.py
backend/workers/prepare_prediction_history.py
docs/operations/AUTOMATIC-DISCOVERY.md
```

Recommended feature commit message after approval:
`feat(discovery): add governed collection and temporal history preparation`.
