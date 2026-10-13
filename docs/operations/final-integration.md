# Final integration sprint — October 13, 2026

## Release status: PARTIAL

The integrated source is on `fix/FE-platform-integration`, based on remote
`develop` SHA `5d5844550682b7c596d958e5420bf3133e981aca` (verified with
`git ls-remote`). Other registered worktrees and their changes were preserved.
No public deployment, real email, production database change, push or merge was performed.

| Module | Status | Evidence and limits |
|---|---|---|
| Live routing and separate `/demo` | COMPLETED (code/build) | Live lazy-loaded by default; fictional demo separately labelled. Browser interaction unverified: no connected browser. |
| Authentication and backend authorization | COMPLETED (API integration) | Registration, `/me`, regular-user admin denial, admin reads and durable logout revocation through disposable HTTP proxy. Tokens remain in memory; refresh requires sign-in. |
| Catalog, search, filters, pagination, details, organizations | COMPLETED (API integration) | Actual database records through client; literal title/description search and filters, page boundaries and detail/error envelopes tested. |
| Saved events and reminder consent | COMPLETED (API integration) | Existing tables; ownership derived from active user. No caller-supplied owner. Default email consent off; strict booleans and allowed keys only. |
| Predictions | COMPLETED (baseline/API integration) | Distinct past catalog dates feed existing baseline. Recurrence advanced to next future cycle; confidence explicitly heuristic. Missing history yields no date. Neural model artifacts remain optional/unverified. |
| Collector → storage → database → API → prediction | COMPLETED (offline fixtures) | Real storage/normalization/ingestion classes with synthetic source data; duplicate skip and invalid-path failure tested. Live source collection is unverified. |
| Reminder scheduling and transport | PARTIAL | Persistent queue, timing, consent rechecks, retry, duplicate claims, templates and disabled/dry-run behavior tested with mocked/forbidden SMTP. No real message sent. Scheduler/provider still need staging configuration. |
| Deployment | PARTIAL | Existing protected workflow and four rendered overlays validated. Container packaging now includes reminder worker, scraper helper and collector dependencies. Docker engine unavailable; container build/PostgreSQL runtime not locally verified. |
| Visual end-to-end acceptance | BLOCKED | Browser automation inventory has no browsers; perform staging browser checklist below. |

## Changed files

- Existing frontend integration preserved and completed: `frontend/src/main.jsx`,
  `Root.jsx`, `App.jsx`, `LivePlatform.jsx`, `DemoPlatform.jsx`, `demo/`,
  `platform.css`, `services/apiClient.js`, `services/authService.js`, auth pages,
  provider, registration validation, `vite.config.js`, `package.json`, tests.
- `backend/app/api/routes/account.py`: saved-event and explicit preference API.
- `backend/app/api/routes/predictions.py`: database-driven baseline catalog forecasts.
- `backend/app/main.py`: include account router.
- `backend/app/schemas/event.py`, `services/event_service.py`: bounded literal search.
- `backend/workers/ingest_collection.py`: offline, transactional collector handoff.
- `backend/tests/test_account_integration.py`: ownership, worker eligibility,
  future forecast and full offline data handoff. Pagination OpenAPI assertion updated
  to include the new search parameter.
- `scripts/disposable_backend.py`: temporary database, Alembic migrations, synthetic
  accounts/events, loopback only, email disabled.
- `backend/Dockerfile`, `.dockerignore`: package operational workers and collector.
- `.github/workflows/ci.yml`: frontend tests and offline collector suite.
- `.gitignore`: exclude disposable support/database/virtual environment.
- `frontend/.env.example`, deployment/worker docs: current environment and API guidance.

## Verification

| Check | Pass | Fail | Skip |
|---|---:|---:|---:|
| Backend suite with freshly installed requirements | 288 | 0 | 0 |
| Offline collector suite | 132 | 0 | 0 |
| Deployment/backup safeguard suite | 31 | 0 | 0 |
| Frontend suite with disposable backend proxy | 16 | 0 | 0 |

Frontend production build passed (1,929 modules); lint passed with no warnings.
`pip check` passed. `scripts/validate_ops.py` passed workflow guards, YAML parsing
and all four Kustomize overlays. Existing migration tests exercise disposable
SQLite upgrade, metadata comparison and downgrade. One backend warning is the
upstream Starlette/httpx deprecation; it does not fail tests.

Initial checks were blocked by sandbox child-process restrictions and missing
system-Python bcrypt; checks were rerun successfully with permitted process access
and project/isolated virtual environments. Contract verification exposed an
existing rejection assertion returning a string; corrected to an explicit boolean.
Contract tests now register a fresh disposable account each run so prior test
preferences cannot affect default-consent assertions.

## Reproduce locally (PowerShell, from this worktree)

```powershell
python -m venv .test-support/venv
.test-support/venv/Scripts/python.exe -m pip install -r backend/requirements.txt -r backend/modules/2.2-collector/requirements.txt
Push-Location backend
../.test-support/venv/Scripts/python.exe -m pytest tests -q
Pop-Location
Push-Location backend/modules/2.2-collector
../../../.test-support/venv/Scripts/python.exe -m pytest -q
Pop-Location
.test-support/venv/Scripts/python.exe -m pytest tests/operations -q
.test-support/venv/Scripts/python.exe scripts/validate_ops.py
```

Use separate terminals for these disposable servers; leave existing servers on
5173/8019 untouched. Each backend start creates a fresh temporary migrated DB.

```powershell
.test-support/venv/Scripts/python.exe scripts/disposable_backend.py
```

```powershell
$env:API_PROXY_TARGET = 'http://127.0.0.1:8020'
npm --prefix frontend run dev -- --port 5174 --strictPort
```

```powershell
$env:FRONTEND_DISPOSABLE_API = 'http://127.0.0.1:5174/api'
npm --prefix frontend run test
npm --prefix frontend run lint
npm --prefix frontend run build
```

Never point this fixture test at a real database/service. Its only accepted proxy
is loopback port 5174. Frontend normal test runs without the environment variable
skip the disposable contract test; that skip is not a pass.

## Deployment commands and requirements

The existing Nginx serves SPA history fallback and proxies `/api/` to backend
root routes. Keep `VITE_API_BASE_URL=/api` for this deployment; Vite variables are
build-time values, not container runtime switches. `API_PROXY_TARGET` is dev-only.
An external-origin API would additionally need explicit backend CORS configuration;
the prepared deployment uses the same origin.

After review and approval, push the integration branch and open a PR to develop.
After its approved merge, wait for CI and image publication on the **merged SHA**.
Provision the namespace, PostgreSQL, registry pull secret, TLS and restricted
kubeconfig as described in `deployment.md`. Set GitHub staging environment variables
`INGRESS_HOST`, `TLS_SECRET`, and secret `KUBE_CONFIG_DATA`. The namespace must contain
`hackathon-db-secret` (`DATABASE_URL` using `postgresql+psycopg://`),
`hackathon-app-secret` (`SECRET_KEY`, random ≥32 characters), `ghcr-creds`, and TLS secret.

After explicit deployment approval:

```powershell
gh workflow run deploy-staging.yml --ref develop -f image_tag=<full-merged-and-published-40-character-SHA>
gh run list --workflow deploy-staging.yml --limit 1
gh run watch <run-id> --exit-status
```

The workflow migrates with `python -m alembic upgrade head` before rolling out.
Do not use the integration commit SHA in place of the eventual protected-branch
CI/publisher SHA. Production dispatch uses `deploy-prod.yml --ref main` only after
the separate approved promotion to main. See `deployment.md` for recovery.

For an approved isolated local/staging Compose target only (configure backend/.env
with that target's PostgreSQL values and signing key first):

```powershell
docker compose build
docker compose up -d db
docker compose run --rm --no-deps backend python -m alembic upgrade head
docker compose up -d backend frontend
```

Do not use these commands against an existing production volume. Compose preserves
its existing PostgreSQL volume; no reset or volume deletion is required.

## Operational jobs

Package includes `workers.email_reminders` and `workers.ingest_collection`.
Use a dedicated external scheduler; do not start jobs per FastAPI web process.

Email: every five minutes, run the following on the approved environment with the
same database/signing config. Keep `EMAIL_MODE=disabled` until a safe destination
and real sending are approved. `dry-run` is a no-op, not a delivered-email test.

```powershell
docker compose run --rm --no-deps backend python -m workers.email_reminders --batch-size 100
```

Configure `EMAIL_MODE=enabled`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_TLS`, `SMTP_TIMEOUT`,
`EMAIL_FROM`, and optional paired `SMTP_USERNAME`/`SMTP_PASSWORD` through a secure
environment file or secret store. Current Kubernetes web deployment deliberately
does not consume SMTP secrets; an approved dedicated worker job must receive them.
SMTP acceptance is not confirmed mailbox delivery. Monitor queue age and
`pending/retry/sending/unknown/failed/accepted`, and follow worker recovery guidance.

Collection: configure an authorized Unstop API source using the existing collector
format. The bundled quotes examples are not hackathon sources. Set `source_id`,
HTTPS API URL, `type=static`, `enabled=true`, and a truthfully recorded
`tos_allows_scraping=true` with permission note; otherwise leave permission false.
Set identifying user agent/contact, persistent raw/log directories and rate limits.
The collector checks robots/access policy and fails closed. No live collection was run.

Run from `backend/modules/2.2-collector` under a dedicated daily scheduler:

```powershell
python run.py --config <approved-sources.json> --source unstop
```

After each successful stored collection, run from `backend`:

```powershell
python -m workers.ingest_collection --storage-root <absolute-raw-storage-root> --location unstop/<collector-generated-stamp>.meta.json
```

The scheduler passes each successful metadata location to ingestion, checks both
exit codes, retains raw/log files, and serializes ingestion per source. Mount those
directories writable by image UID 10001 when using containers. Duplicate source/URL
rows are skipped; the schema has no concurrency uniqueness constraint, so use one
ingestion writer. There is one fetched page per source; do not assume full-site coverage.

## Remaining approval and acceptance steps

1. Review integration diff/PR summary and approve push/PR/merge as desired.
2. Start Docker and run CI container builds and disposable PostgreSQL migrations;
   existing CI provides the PostgreSQL test service and build jobs.
3. Supply approved staging infrastructure/domain/secrets, then approve staging dispatch.
4. In a browser: open `/`, register/log in, search/filter/page, open detail and
   organizer link, inspect predictions, save event, opt in/out, switch accounts,
   verify regular-user admin denial, log out, refresh a detail route, and open `/demo`.
5. Approve source collection and configure its dedicated schedule/handoff.
6. Provide a safe email destination and approval for actual sending; configure
   reminder schedule/provider, confirm received content, opt-out and deduplication.

The MVP code is integrated and locally API-tested. Deployment, visual journey,
live collection and real mailbox delivery remain explicit acceptance gates before
the October 18, 2026 deadline.
