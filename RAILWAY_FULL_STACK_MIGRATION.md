# Full-stack Railway cutover — Hackathon Radar Finder

Status: **prepared, not deployed**. This is an execution checklist, not evidence of a
Railway account connection, running service, backup, successful restore, or public launch.
Keep Render, Cloudflare Workers and Supabase serving until the Railway stack passes
acceptance. Source branch: `develop`; preserve required PR and CI review.

## Scope and observed starting point (2026-11-09)

Move the **entire** application to one Railway project:
1. PostgreSQL, persistent private database/volume
2. FastAPI backend, private service
3. React/Vite frontend served by Nginx, public Railway domain
4. Python collector, private one-replica worker with its own persistent snapshot volume
5. Optional in-app reminder worker (email transport stays disabled)

Existing source is already Railway-aware:
- `backend/Dockerfile`: Uvicorn listens on `0.0.0.0:8000`.
- `frontend/Dockerfile`: Vite builds; Nginx serves on `8080`, proxies `/api/`
  to the private backend, and supports SPA refreshes.
- `backend/workers/migrate.py` and `backend/workers/railway_collector.py` exist.
- See `RAILWAY_DEPLOYMENT.md` for exact variables and constraints.

Read-only Supabase inspection on 2026-11-09 found the **production**
`hackathon-radar-db` project at revision `f1a2b3c4d5e6`, with **estimated**
table counts: `institutions=54,522`, `hackathons=9`, `users=6`.
Obtain fresh exact counts at export time. The separate
`hackathon-radar-staging` project does **not** contain those records and must
not be used as the migration source. Its tables also have an unresolved RLS
security warning; do not publish its Supabase API or copy its access settings.

## Access, cost and safety gates

- Connect Railway to the owner-approved GitHub organization/repository, and
  confirm Railway plan, credits and spending limits. A free allowance does not
  guarantee uninterrupted hosting of a database plus multiple services.
- Keep secrets in Railway variables only, not source control or chat. Do not print
  connection strings, passwords, JWT signing keys or restore files to logs.
- Verify ownership and availability of Supabase backup credentials and the
  destination PostgreSQL connection from a secure workstation. PostgreSQL 17
  client tools are appropriate for the current Supabase Postgres 17 source.
- Verify database backup and **trial restore** to a disposable destination.
  Record exact pre-cutover table counts and migration revision.
- Prevent application writes and stop all collectors **briefly for final snapshot**,
  or use a formally reconciled incremental migration. Without this, a dump taken
  while writes continue can lose newly created accounts, saves or event changes.
- No provider services, paid resources, DNS changes or production data deletions
  should be represented as completed without confirmation.

## Railway service configuration

Create a Railway project with a `staging` environment first. Import the **same**
GitHub monorepo separately for backend, frontend and collector. Root paths
are service-scoped and do not require copying Compose:

| Service | Root and image | Start / release | Network / health |
| --- | --- | --- | --- |
| Postgres | Railway PostgreSQL template | Provider managed | Private; volume and backup |
| Backend | `/backend` (`Dockerfile`) | Docker CMD; **pre-deploy** `python -m workers.migrate` | Private; `PORT=8000`; `/ready` |
| Frontend | `/frontend` (`Dockerfile`) | Nginx image CMD | Public Railway domain; `PORT=8080`; `/health` |
| Collector | `/backend` (`Dockerfile`) | `python -m workers.railway_collector` | Private; one replica; mount `/app/collector-data` |
| In-app reminders (optional) | `/backend` | `python -m workers.in_app_reminders --watch` | Private |

Backend and collector Railway variables:
```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
ENVIRONMENT=production
DEBUG=false
EMAIL_MODE=disabled
API_V1_PREFIX=/api/v1
SECRET_KEY=(independently generated random secret >=32 characters, configured privately)
```
Use the actual Railway database service reference; a separate secret must be set
per environment. Changing `SECRET_KEY` invalidates existing signed sessions;
if preserving sessions is required, transfer the old secret securely.

Frontend variables (names must match actual Railway service names):
```text
PORT=8080
BACKEND_HOST=${{Backend.RAILWAY_PRIVATE_DOMAIN}}
BACKEND_PORT=8000
```
The frontend only receives same-origin `/api` calls; never supply DB keys or
backend JWT secrets as `VITE_*` variables. Railway must start a backend using
the current Dockerfile with a listening port of `8000`.

Collector variables, **only after the application and evidence volume are ready**:
```text
COLLECTOR_SNAPSHOT_DIR=/app/collector-data
COLLECTOR_RAW_DATA_DIR=/app/collector-data/raw
RAILWAY_RUN_UID=0
DISCOVERY_ENABLED=true
COLLECTION_ALLOW_LIVE=false
```
Keep live acquisition disabled until provider credentials, permitted source
coverage and review controls are checked. Do not silently auto-publish candidates.

## Database migration order (one-time, secure workstation)

1. Create **an empty Railway PostgreSQL database** and confirm a persistent
   volume/backup strategy, project region, and PostgreSQL compatibility.
2. Collect exact, current source counts and its `alembic_version`.
3. Pause writers/collectors for the final backup. Use `pg_dump` to create a
   password-protected, access-controlled custom-format archive from the **production**
   Supabase PostgreSQL connection. For a typical application-only export:
   ```sh
   pg_dump --format=custom --no-owner --no-acl --schema=public --file=radar-prod.dump "$SOURCE_DATABASE_URL"
   ```
   Use secure local environment variables; do not paste credential URLs into Git.
   Validate what public-schema objects and extensions the archive contains.
4. Test the archive against a **disposable empty Railway database**, with matching
   extensions and roles as required. Only on a verified empty target:
   ```sh
   pg_restore --exit-on-error --single-transaction --no-owner --no-acl --dbname="$TARGET_DATABASE_URL" radar-prod.dump
   ```
   Do not pass `--clean` or run on an existing populated production database.
   Resolve unsupported Supabase-specific extensions, policies or ownership in the
   disposable test restore before repeating against the intended empty target.
5. Verify exact counts, schema, indexes, constraints, foreign keys, user logins
   and `alembic_version`. Never log private row contents. Example read-only SQL:
   ```sql
   SELECT (SELECT COUNT(*) FROM public.institutions) AS institutions,
          (SELECT COUNT(*) FROM public.hackathons) AS hackathons,
          (SELECT COUNT(*) FROM public.users) AS users,
          (SELECT version_num FROM public.alembic_version LIMIT 1) AS revision;
   ```
6. Repeat the verified restore against the intended empty Railway database
   from the final frozen snapshot. Deploy the backend with its migration
   pre-deploy command, after the restored schema is in place.
7. Keep the old Supabase database untouched for rollback. Do not provision a
   second blank database and point production there by mistake.

## End-to-end acceptance before traffic cutover

- Railway frontend `/health` and proxied `/api/ready` both respond correctly.
- Sign-up/login/logout, existing account login, saved events and authentication
  permissions work over the **Railway frontend origin**.
- University listing, state/district filters, institution count, public events,
  details, provenance and pagination use the restored data (not demo fixtures).
- Browser refreshes and deep links resolve; all API paths stay same-origin;
  API responses are not publicly cached.
- No SMTP, OTP or publicly uncalibrated ML features are accidentally enabled.
- Collector volume survives restart, runs as the restricted application user
  after bootstrap, and is single-replica. Enable collection only after source
  permission and credentials are verified.
- Record the real domain, deploy IDs, exact counts, readiness, CI status and
  database backup/restore test evidence.

Only after acceptance, update users/bookmarks to the verified Railway frontend
domain or migrate a verified owned custom domain. Keep the old stack and a
known-good database backup temporarily. A rollback after new writes requires
reconciling those writes; changing DNS alone can lose user changes. Decommission
Render/Cloudflare/Supabase only with explicit owner approval and retained backups.
