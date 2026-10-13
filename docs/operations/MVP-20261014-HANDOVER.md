# October 14 MVP handover

Verified locally on October 13, 2026. Integration base and remote `develop` both
equal `6087968a766d4fabd6a06d19650c242100b02cff`.

## A. Overall status

Operational local MVP, verified through HTTP and disposable database integration.
Browser visual acceptance and public deployment remain incomplete. This is not
a claim of full SRS compliance or production approval.

Branch: `fix/MVP-20261014-local-completion` in `.release-local`.
Implementation commit: `0fc3601cccfcc83b341506feca8415a87c8e5646`.
The subsequent handover commit contains this report and the updated deadline.
No remote push, merge or cloud deployment was performed. Existing worktrees and
their modifications were retained.

## B. Completed work

- Inspected and applied additive migrations `b7c8d9e0f1a2` and `c8d9e0f1a2b3`.
  Live Alembic revision is `c8d9e0f1a2b3`; revocation and delivery tables exist.
  No migration downgrade or data reset was executed.
- Retained volume `hackathonradarfinder_radar_postgres_data`. Database and
  application containers were recreated as necessary; the volume was not.
  PostgreSQL 16, backend and frontend are all healthy.
- Fixed the occupied frontend port by supporting `FRONTEND_PORT`; this release
  runs on loopback port **5175**. The existing process on 5173 was preserved.
- Replaced the public notification placeholder with authenticated, account-owned
  latest-100 notice reads and persistent mark-read. A first successful save
  creates a notice in the same transaction; duplicate saves do not duplicate it.
- Added an offline curated importer with full-batch validation, HTTPS provenance,
  explicit `--apply`, caller-controlled transaction and URL duplicate prevention.
  It never fetches websites or overwrites existing events. Run one writer only.
- Imported five genuine records across three organizations. Second import:
  **0 inserted, 5 duplicates**. No synthetic event was added to the live database.
- Added explicit unconfirmed prediction labels and historical source links.
  Estimates use the existing mean-gap baseline; no advanced model was trained.
- Preserve day-only dates as UTC-midnight calendar representations, disclose
  that convention in descriptions, display dates without invented times, and
  exclude these records from timed email enqueueing. Unpublished deadline times
  remain null. This is an MVP convention, not a general date-precision schema.
- Added guarded local live-smoke and disposable PostgreSQL runtime checks.

### Genuine event provenance

All records are a manually reviewed snapshot of publicly published facts, not
an automated scrape. Only concise original factual summaries are retained.

| Record | Organizer source | Published dates | State on October 13 |
| --- | --- | --- | --- |
| HackHarvard 2026 | [Organizer](https://hhuh.io/) | October 16–18, 2026 | Upcoming; applications closed |
| MIT Policy Hackathon 2026 | [Organizer FAQ](https://www.mitpolicyhackathon.org/faq2026) | November 20–22, 2026 | Upcoming; applications close October 14, exact time unpublished |
| Megathon X 2026 | [Organizer](https://megathon.in/) | October 10–11, 2026 | Historical |
| Megathon 2025 | [IIIT Hyderabad](https://www.iiit.ac.in/megathon-2025-11-and-12-october-2025-3/) | October 11–12, 2025 | Historical |
| Megathon 2022 | [E-Cell retrospective](https://ecell.iiit.ac.in/events/hackathons/megathon-22.html) | October 22–23, 2022 | Historical |

Manifest: `backend/data/curated-mvp-20261013.json`. Existing collector source
configuration contains quotes demo sources without scraping approval. The
Unstop adapter works in tests, but no approved live source configuration was
found. Those automated sources were skipped; no permission flag was invented
and no robots/403/CAPTCHA restriction was bypassed.

### Database and backups

Live checks: 5 hackathons, 3 organizations, no orphan event organizations,
no unvalidated PostgreSQL constraints, and zero email delivery rows.
Smoke checks created two explicitly named local smoke accounts with random
in-memory credentials, genuine saved events and notices. Both ended logged out
and opted out of email. Credentials were not recorded or printed.

Original backup remains accessible:
`C:\Users\nakul\HackathonRadarBackups\radar-20261013-083329.dump`.
Its archive index was readable; its earlier restore test is user-supplied evidence.
A separate post-migration backup was created at:
`.test-support/backups/radar-mvp-20261013-090922-d2e45e.dump`.
Git ignores this directory. That new backup was restored successfully into a
network-isolated disposable PostgreSQL 16 tmpfs container: revision head,
5 events, 3 organizations, zero unvalidated constraints. The test container was
stopped afterward. No restore targeted the existing database.
The new backup is local evidence, not durable off-host backup scheduling.

## C. Verification

| Check | Result |
| --- | --- |
| Backend and operations suite | 362 passed; one existing Starlette/httpx deprecation warning |
| Collector suite | 132 passed |
| Frontend suite, including disposable API fixture | 16 passed, zero skipped |
| Final frontend lint and production build | Passed, no lint warnings |
| Backend/frontend Docker builds | Passed; final images running |
| Compose config validation | Passed without printing resolved settings |
| Workflow guards, action pins, YAML | Passed |
| Kustomize dev/test/staging/prod | Passed, 9 resources per overlay; no cluster contacted |
| Disposable PostgreSQL 16 runtime | Migration head, ownership, DB roles, notices, consent, delivery dedup, mocked SMTP and revocation passed |
| New backup restore | Passed only in disposable PostgreSQL 16 |
| Live Nginx API journey | Registration/login/me, denied regular-user admin, search/filter/detail, save/unsave, saved persistence, consent, read notices, logout revocation passed |
| Live prediction catalog | Three organization responses; Megathon has 3 genuine historical dates and an unconfirmed heuristic estimate; others correctly have insufficient history |
| Email disabled and dry-run CLI | No-op, queued 0/accepted 0; no messages sent |
| SPA route refresh | `/event/1` returns the frontend root successfully |
| Git whitespace checks | Passed |
| Browser visual/responsive acceptance | Skipped: UI tool inventory had no browsers or apps |
| Public hosting, real SMTP acceptance, cluster rollout/rollback | Skipped: external setup and authorization absent |

Initial test invocation lacked `PYTHONPATH`; corrected to the release backend.
Two legacy tests initially expected public placeholder notifications; updated
to assert 401 for private account notices. Final suite is green.
Disposable SQLite/Vite fixture servers were stopped; unrelated local processes
were preserved. All SMTP-enabled runtime checks replaced the transport with a mock.

## D. Remaining blockers and SRS boundaries

For tomorrow's local demo: perform human browser acceptance, especially register,
login, mobile navigation, refresh, source links and notification controls.
For public release: explicit hosting/deployment approval, a provisioned environment,
DNS/HTTPS, protected CI/image publishing and successful staging acceptance are
required. No public URL was deployed or verified.

| SRS category | MVP evidence | Remaining requirement/evidence |
| --- | --- | --- |
| Discovery/catalog | Five genuine manually sourced records; tested compliant collector | Approved source registry records, scheduled collection and freshness monitoring |
| Authentication/security | DB-owned roles, saved-item ownership and persisted revocation | Full security assessment, abuse/rate limits, password reset; public TLS acceptance |
| Predictive intelligence | Real historical dates, visible evidence, unconfirmed heuristic | Calibrated confidence/date windows, representative history, evaluation metrics and advanced ML |
| Reminders | Consent/persistence, dedup/retries/templates tested | Authorized SMTP destination, real delivery acceptance, reviewed scheduler; day-precision schema |
| Administration | Actual DB statistics and DB role enforcement tested | Source status integration, review workflows, audit/comprehensive management |
| Accessibility/responsiveness | Existing responsive styling and semantic controls build | Human/browser accessibility, keyboard and mobile acceptance |
| Operations | Local migrations, health, backup restore, static deployment checks | Durable encrypted/off-host backups and retention, monitoring, DB readiness probe, staging rollback rehearsal |

No full Hackathon Radar AI SRS v1.0 document was found in this worktree. This
category matrix follows the supplied brief; requirement-by-requirement sign-off
needs the actual SRS and acceptance evidence. Missing editions can strongly
distort the recurrence estimate; do not present it as an organizer announcement.
The live notification producer covers save confirmations; scheduled in-app
event reminders are not implemented. `/health` remains process liveness; real
DB connectivity was established by catalog/account requests, not by that probe.

## E. Exact local commands and deployment path

PowerShell from the repository root:

```powershell
Set-Location 'C:\Users\nakul\OneDrive\Documents\Desktop\hackathonradarfinder'
$env:FRONTEND_PORT = '5175'
docker compose -p hackathonradarfinder -f .release-local/docker-compose.yml config --quiet
docker compose -p hackathonradarfinder -f .release-local/docker-compose.yml up -d --build backend frontend
docker compose -p hackathonradarfinder -f .release-local/docker-compose.yml exec -T backend alembic current
Invoke-RestMethod 'http://127.0.0.1:5175/api/health'
Invoke-RestMethod 'http://127.0.0.1:5175/api/events/?page=1&page_size=10'
```

Frontend: **http://127.0.0.1:5175**.
Backend: **http://127.0.0.1:8000**, docs: **http://127.0.0.1:8000/docs**.
The frontend uses same-origin `/api/`; Nginx forwards to backend port 8000.
Port 5173 belongs to a preserved unrelated process. Set `FRONTEND_PORT` for each
Compose invocation so the release frontend stays on 5175.

The migrations have already been applied. Do not downgrade the live database.
After reviewing future migrations and confirming a current backup, the existing
upgrade command is:

```powershell
docker compose -p hackathonradarfinder -f .release-local/docker-compose.yml run --rm --no-deps backend alembic upgrade head
```

Safe worker verification (neither command sends email or previews rendered mail):

```powershell
docker compose -p hackathonradarfinder -f .release-local/docker-compose.yml exec -T -e EMAIL_MODE=disabled backend python -m workers.email_reminders --batch-size 10
docker compose -p hackathonradarfinder -f .release-local/docker-compose.yml exec -T -e EMAIL_MODE=dry-run backend python -m workers.email_reminders --batch-size 10
```

For repeat import of this reviewed snapshot only:

```powershell
docker cp .release-local/backend/data/curated-mvp-20261013.json hackathon-radar-backend:/tmp/curated-mvp.json
docker compose -p hackathonradarfinder -f .release-local/docker-compose.yml exec -T backend python -m workers.ingest_curated /tmp/curated-mvp.json
docker compose -p hackathonradarfinder -f .release-local/docker-compose.yml exec -T backend python -m workers.ingest_curated /tmp/curated-mvp.json --apply
```

Fastest supported public path is the existing Kubernetes staging workflow, if a
cluster is already provisioned. No evidence of a ready cluster was supplied.
Local Compose is a loopback demo configuration, not a production hosting plan.
After approval, push/review this branch through a PR targeting **develop**,
then require successful CI and GHCR publishing for the resulting full develop SHA.
Provision environment-scoped `KUBE_CONFIG_DATA`, namespace `hackathon-staging`,
secrets `hackathon-db-secret`, `hackathon-app-secret`, `ghcr-creds`, a TLS secret,
and GitHub variables `INGRESS_HOST`/`TLS_SECRET`; verify PostgreSQL persistence,
backup and reviewed migrations. Keep SMTP disabled until explicitly approved.

Only after external deployment authorization, substitute the approved published
40-character SHA and run:

```powershell
gh workflow run deploy-staging.yml --ref develop -f image_tag=APPROVED_FULL_DEVELOP_SHA
```

Verify HTTPS frontend, `/api/health`, real catalog, browser account journeys and
staging application rollback before production promotion. The existing production
workflow is `deploy-prod.yml`, gated on reviewed `main` promotion and the
`production` environment; it is not authorized by this local completion task.
Do not equate database restoration with application rollback.

## F. October 14 demonstration

1. Open `http://127.0.0.1:5175`; show the real source-backed catalog.
2. Search `HackHarvard`, inspect the organizer link and closed-application caveat.
3. Filter Hyderabad/In-Person; explain these are historical Megathon editions.
4. Register a demo account in the UI, sign in, save a genuine event, inspect
   Saved events, then unsave and save again. Sign out/in to show persistence.
5. Open Predictions: expand historical evidence, explain unconfirmed heuristic
   confidence, missing editions and the insufficient-history states.
6. Open Preferences: change consent, save/reload, and mark the saved-event notice
   read. Explain that email is disabled and no email has been sent. Leave consent off.
7. Show a regular user cannot access Admin. Admin statistics and DB role behavior
   were tested in disposable PostgreSQL; do not grant production privileges for a demo.
8. Sign out; show protected account access requires authentication.

Recommendation: demonstrate this verified local MVP on October 14, with these
limitations disclosed. Public launch and full SRS acceptance need the remaining
external and browser checks; advanced ML and disaster-recovery automation should
not displace local-demo acceptance.
