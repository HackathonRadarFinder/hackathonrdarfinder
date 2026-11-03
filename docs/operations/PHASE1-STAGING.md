# Phase 1 — controlled staging and release protection

Architecture: Supabase PostgreSQL, Render Free Docker backend, Cloudflare Pages React frontend. This document prepares changes; it does not authorize a push, merge, deploy, database migration, import, account creation or live collection.

## Changes and root causes

| Blocker | Root cause | Fix |
|---|---|---|
| Two Module 2.4 failures | `save_master()` caught edition conflicts and committed partial batches; pipeline replaced review artifacts despite conflict | Fail-fast `BEGIN IMMEDIATE` transaction covers schema upgrades, identity resolution, canonical rows, links and history. Input IDs update only after commit. Competing writers serialize. Complete JSON files replace under the same writer lock and are restored on ordinary publication/commit failure. |
| Pages returns HTML for API calls | Vite/Nginx proxy is absent from static Pages deployment; SPA fallback swallowed `/api/*` | `functions/api/[[path]].js` forwards to the fixed HTTPS Render origin; `_routes.json` reserves `/api` and `/api/*` for Functions. |
| 12 Windows fixture setup errors | `read_text()` normalized CRLF before hashing while tests hashed evidence bytes | Read fixture bytes and decode without newline normalization; LF checkout policy plus explicit LF/CRLF regression coverage. |
| Failed checks can reach hosting | Render's Git integration deployed on commit independently of Actions | Required aggregate `release-gate` fails on failure/cancellation/skip, including PostgreSQL images/Pages/Windows checks; publisher still waits for the full reusable CI workflow. **Provider automatic deployment settings require owner changes below.** |
| TCP health and migration-on-start | Existing Render command migrated on every startup; HTTP health path was blank | Prepared `render.phase1.yaml` uses `/ready` and `workers.check_ready`, a bounded read-only gate before Uvicorn. No migration/import occurs in this startup command. |
| Sensitive failure diagnostics | Unexpected exception tracebacks could include driver parameters/config values | Generic error-class/request-ID logging, SQLAlchemy hidden parameters, bounded safe request IDs, Pydantic startup input redaction. OpenTelemetry API updated to1.45.1 for the audited advisory. |

The main SQLAlchemy duplicate-review service and Module 2.4 SQLite pipeline are distinct. Existing PostgreSQL acceptance tests additionally verify concurrent reviewed imports, preservation of existing manual facts, transaction rollback, review publication, saves and revocation. No automatic approval/publication is introduced.

SQLite is authoritative for the offline Module 2.4 pipeline. Independent files and a database cannot share a crash-atomic commit: an OS/process crash between output renames and SQLite commit may require rerunning/reconciling review exports. Ordinary errors restore prior artifacts and roll back the batch; tests cover late conflicts, competing writers and a second-file replacement failure. Exports remain offline review artifacts, not an automatic publication feed.

## Local verification

Use Python3.12 and Node24 in an isolated environment. PowerShell examples use a checkout-local `.venv`; another isolated interpreter can be substituted. Do not load a production `.env` into tests.

```powershell
python -m venv .venv
& .venv/Scripts/python.exe -m pip install -r backend/requirements.txt -r backend/radar_collector/requirements.txt -r backend/modules/2.2-collector/requirements.txt -r backend/modules/2.4-dedup/requirements.txt
$env:RADAR_TEST_PYTHON=(Resolve-Path .venv/Scripts/python.exe).Path
Push-Location backend
& ../.venv/Scripts/python.exe -m pytest tests radar_collector/tests -q
Pop-Location
Push-Location backend/modules/2.4-dedup
& ../../../.venv/Scripts/python.exe -m unittest discover -v
Pop-Location
Push-Location frontend
npm ci
npm test
npm run lint
npm run build
$env:WRANGLER_SEND_METRICS='false'
npm run build:pages
npx playwright-core install chromium
npm run test:pages
Pop-Location
```

`test:pages` starts its own loopback temporary SQLite backend, verifies its disposable marker, loads the actual Wrangler-generated Pages router in local workerd, and intercepts **every** backend fetch into that fixture. It tests `/api/auth/status`, paginated events, a401 JSON login failure, SPA document refresh, the full API-client account journey and browser/axe acceptance. It never sends these authentication writes to Render/Supabase. The test assets binding models static dist/SPA serving; provider CDN behavior still needs an approved preview check. Test-only upstream interception is not a production binding/URL override.

For PostgreSQL16 and image/browser acceptance with Docker available:

```powershell
docker build -t hackathon-radar-backend:test backend
docker build -t hackathon-radar-frontend:test frontend
& .venv/Scripts/python.exe scripts/postgres_acceptance.py --backend-image hackathon-radar-backend:test --frontend-image hackathon-radar-frontend:test --out .test-support/phase1-pg16
```

Do not point tests at an existing database. The Docker runner creates an owned tmpfs PostgreSQL16 container and checks its identity before writes. Where Docker is unavailable, the optional native launcher creates a **new** password-protected loopback cluster and random database, verifies its data directory/marker/role/address/port before migration/test writes, and stops it afterward:

```powershell
& .venv/Scripts/python.exe scripts/native_postgres_acceptance.py --pg-bin 'C:\Program Files\PostgreSQL\18\bin'
```

The launcher supports installed16/18 binaries only, never reuses a Windows PostgreSQL service, and leaves the stopped disposable cluster under `.test-support/native-postgres` for inspection. Version18 evidence is useful but does not replace canonical16 Docker/image acceptance. No generated password is printed or included in manifests. PostgreSQL tests skip in ordinary SQLite runs by design.

## Owner actions before any push or merge

1. **Disable Render automatic deployment on the verified existing service** `srv-dbik82mtlv9c73avbprg` (`hackathonrdarfinder`) before pushing/merging a branch that hosting may watch. Do not apply a Blueprint as a new service inadvertently. Keep deployments manual through controlled staging. Later `After CI Checks Pass` may be considered, but note that Render accepts some skipped/neutral conclusions; require the explicit always-running `release-gate` and branch restrictions as well.
2. **Disable Cloudflare Pages automatic production deployment and unapproved preview builds.** Preview branches can deploy even when production is disabled. Verify production branch and custom preview include/exclude rules. No feature branch has been pushed by this work.
3. **Protect both develop and main.** Require PRs, review by an owner, dismissal of stale approval, up-to-date accepted checks/merge queue as appropriate, no direct/force pushes or branch deletion, and restricted/admin bypass. Require the `release-gate` check emitted by workflow `CI` after the first proposed PR run; use the actual check identity shown in GitHub. Do not allow a skipped Docker/Pages/Windows job to count as release acceptance. Add environment reviewers for staging/production changes.
4. GitHub branch-protection GETs returned403 `Resource not accessible by integration` for both branches. Existing protection could not be verified and cannot be changed through the installed connection. This is an integration permission limitation, not proof that protection is absent. Owner/admin must inspect/apply it.
5. Confirm the operator's credential-rotation date and affected DB role. Operator has confirmed that the old Supabase credential was rotated/revoked; date/role were not supplied. Record metadata only, never values. Do not retrieve or retest the old password. New settings must use the rotated existing credential through provider secret storage.

Existing `.github/workflows/deploy-{dev,test,staging,prod}.yml` are manual, provenance-gated **legacy Kubernetes** flows. They were inspected and remain gated; do not invoke them for the selected Render/Pages/Supabase architecture. `build-and-publish.yml` cannot publish images until the full reusable CI succeeds. No new remote deployment job is introduced in Phase1.

## Prepared Render changes — explicit approval required to apply

`render.phase1.yaml` is a review-only configuration for the existing Free Docker backend: root `backend`, `./Dockerfile`, `/ready`, auto-deploy off, and:

```sh
/bin/sh -c 'python -m workers.check_ready && exec uvicorn app.main:app --host 0.0.0.0 --port 8000'
```

Keep existing private `DATABASE_URL` and `SECRET_KEY`; `sync:false` is an initial-create prompt, **not** secret rotation or a way to update an existing secret. No Render database, frontend, worker, disk or paid plan is added. Current public Render JSON schema validation passed; CLI/provider semantic validation has not been run. Prefer targeted Dashboard changes on the verified service unless the owner deliberately adopts/syncs this Blueprint. Saving provider settings may deploy; inspect the selected action before confirming.

`/health` is liveness only. `/ready` compares all shipped Alembic heads with the database and returns503 for missing/unreachable schema or wrong revision. PostgreSQL checks use a read-only transaction and1.5-second statement timeout. Connection/pool waits are bounded at2 seconds. Readiness checks do not create tables, migrate or import. Startup makes at most3 checks with2-second gaps; stale revision fails immediately. A missing migration table may be retried as unavailable, but still never modified. Apply any needed migration separately only after backup/DB-identity review and explicit release authorization; stale schema intentionally blocks startup.

Render Free can sleep after15 minutes; wake-up can exceed the proxy's25-second timeout. The proxy returns sanitized503/504 JSON and a retry hint instead of provider HTML. It performs **no automatic retry of login/register/save writes**. Test a cold and warm request during approved preview verification; do not promise continuous worker execution or availability from this configuration.

## Prepared Cloudflare Pages changes

- Root: `frontend`; Node24; install/build: `npm ci && npm run build:pages`; output: `dist`.
- The `functions` directory belongs at the Pages project root beside frontend source, **not inside dist**. Git-integrated Pages builds discover it. `_routes.json` is copied from `public` into dist; include both `/api` and `/api/*` and no exclusion. Choose Functions fail-closed behavior on quota exhaustion so API routes cannot turn into static fallback.
- `wrangler.toml` specifies Pages output and compatibility date. Wrangler4.156.2 and its local runtime are pinned in the lockfile. `build:pages` compiles a separate local worker under `.test-support/pages-worker` for verification; it does not deploy.
- Leave `VITE_API_BASE_URL` unset or `/api`. Never put secret keys, database URLs or bearer tokens in `VITE_*`. Do not change it to the direct Render origin as a proxy workaround; backend CORS is intentionally not opened in this fix.
- Proxy origin is exactly `https://hackathonrdarfinder.onrender.com`. Client path/query/headers/bindings cannot choose a different host. It forwards method/query/body and allowlisted Accept/Content-Type/Authorization, replacing untrusted request IDs. Cookies, Host/forwarding and Cloudflare identity headers are not forwarded. Backend JSON status/body and necessary response headers are retained; private responses are no-store. Same-origin backend redirects are rewritten under `/api`; external/credentialed redirects fail502 and are never followed with bearer credentials. Request/response payloads are bounded at4MiB; timeout25 seconds. Oversized requests fail413 before forwarding. Non-JSON provider HTML and invalid JSON become sanitized failures; no exception/body/credentials are logged by the proxy.
- Do not deploy uncompiled source as a standalone Worker. Do not delete the previously reported mistaken Worker until owner verifies its identity and approves removal.

## Controlled staging verification

The requested production proxy is deliberately fixed to the existing Render origin. A Pages preview alone is therefore **not isolated staging**: its API traffic still goes to that backend/database. Do not create test users, save records, review candidates or import data through that preview without explicit permission.

After owner-approved deployment, safe read-only checks against the approved preview URL are:

```powershell
$preview='https://OWNER-VERIFIED-PREVIEW.pages.dev'
Invoke-RestMethod "$preview/api/auth/status"
Invoke-RestMethod "$preview/api/ready"
Invoke-RestMethod "$preview/api/events/?page_size=1"
# Empty JSON validates forwarding to FastAPI without valid credentials/account writes.
Invoke-WebRequest "$preview/api/auth/login" -Method Post -ContentType 'application/json' -Body '{}' -SkipHttpErrorCheck
Invoke-WebRequest "$preview/login"
```

Expected: auth/status200 JSON; ready200 JSON (or truthful503); events200 expected message/data/total/page/page_size; empty login422 JSON with backend error envelope; login document200 compiled React. Refresh `/login`, `/explore`, `/universities` and a valid event route; assets load, API routes never return HTML. Empty production catalog/directory are still truthful data gates, not fixed by this phase.

For hosted **write** acceptance, first approve a separate Supabase staging database/branch and Render staging service, independent signing secret, disabled collection/email and synthetic staging-only data. A reviewed staging-specific proxy origin change must pin that exact verified service; do not add an arbitrary upstream URL override. Provisioning, costs, migrations and deployment require owner approval. Run signup/login/logout/expiration/revocation/profile/save/unsave/filter/permissions with explicitly authorized staging accounts only. Current local workerd acceptance already exercises these writes solely on its marked disposable fixture.

Roll back applications to the previously accepted Pages deployment/Render commit with compatible schema. Do not reset volumes, restore over production, downgrade Alembic or re-enable compromised credentials. Any data restore is a separately approved operation into an isolated target first.

## Remaining release gates

Remote CI has not run this unpushed branch. PostgreSQL16 Docker/image/browser acceptance remains required because Docker Desktop's Linux daemon is unavailable locally. Provider health/auto-deploy/Pages configuration and branch protection are prepared/documented, not applied. Operator rotation date/role, approved dataset population, monitoring/backups and Phase2 product/security work remain outside this phase. Do not enable scraping, imports, public unvalidated forecasts or real email as part of the staging check.

References checked3 November2026: [Pages routing](https://developers.cloudflare.com/pages/functions/routing/), [Pages local development](https://developers.cloudflare.com/pages/functions/local-development/), [Pages branch controls](https://developers.cloudflare.com/pages/configuration/branch-build-controls/), [Render health checks](https://render.com/docs/health-checks), [Render deploys](https://render.com/docs/deploys), [Render Blueprint spec](https://render.com/docs/blueprint-spec), [Render env vars](https://render.com/docs/configure-environment-variables), [Render Free](https://render.com/docs/free).
