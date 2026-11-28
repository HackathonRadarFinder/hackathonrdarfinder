# Railway and Cloudflare deployment

Status: local integration under verification; no provider project, database,
deployment, domain, certificate or public URL has been verified for this change.
Branch: `feat/railway-cloudflare-production-deployment`; PR target: `develop`.
Never deploy production from this feature branch or automatically merge main.

## Native service settings

Use one project with an isolated **staging** environment first. Reuse the existing
Dockerfiles; do not upload Compose. Configure these settings through Railway's
native GitHub integration. No provider credentials belong in GitHub source files.
Railway's current documentation deprecates legacy `railway.json`/`railway.toml`
for new services, so this change does not add duplicate legacy deployment files.

| Service | Source root / image | Start / release command | Networking / health |
| --- | --- | --- | --- |
| PostgreSQL | Railway PostgreSQL template, persistent volume | Provider default | Private only; remove any TCP proxy |
| Backend | `/backend`, existing Dockerfile | Existing Uvicorn CMD; **pre-deploy:** `python -m workers.migrate` | Private; `PORT=8000`; `/ready`, timeout 120s |
| Frontend | `/frontend`, existing Dockerfile | Existing Nginx CMD | Public generated domain, target port 8080; `PORT=8080`; `/health` |
| Collector | `/backend`, existing Dockerfile | `python -m workers.railway_collector` | Private; one replica; persistent `/app/collector-data` volume |
| Migrations | Backend release phase, not a continuously running service | `python -m workers.migrate` | Internal; must succeed before backend rollout |

Set backend/frontend restart policy to on failure with bounded retries (10).
Keep collector **undeployed** until its variables, volume and schema are ready;
then use always-restart with failure alerts. Railway deployment health checks
gate rollout, not continuous monitoring. Configure external uptime/failure alerts
before production traffic. No public backend or PostgreSQL domain is needed.

For a new environment, Railway private DNS has IPv4 and IPv6. This integration
uses IPv4 DNS resolution and the existing `0.0.0.0:8000` backend listener. An old
IPv6-only environment is unsupported by these settings: create a new staging
environment rather than exposing the backend publicly to work around it.

## Variables (values are configured privately in Railway)

Backend and collector:

| Variable | Value / policy |
| --- | --- |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}`, using the **private** host; adapt service reference to its actual name |
| `SECRET_KEY` | Generated independently per environment, at least 32 random characters; same within an environment |
| `ENVIRONMENT` | `production` for production; `staging` for staging |
| `DEBUG` | `false` |
| `EMAIL_MODE` | `disabled`; leave SMTP credentials unset |
| `API_V1_PREFIX` | `/api/v1` |

The PostgreSQL URL validator selects the installed psycopg driver without changing
URL credentials, encoding or query parameters. Never print the URL for diagnosis.
Migration workers use a bounded PostgreSQL session advisory lock and the same
connection as Alembic. A failed release command blocks backend startup. Do not
run it locally against `backend/.env`. Release phases do not require collector
volumes. Deploy one migration owner per environment; do not change schemas from
frontend or collector startup. Rolling schema changes still require backwards
compatibility with the old backend during rollout.

Frontend only:

| Variable | Value |
| --- | --- |
| `BACKEND_HOST` | `${{Backend.RAILWAY_PRIVATE_DOMAIN}}`, using actual backend service name |
| `BACKEND_PORT` | `8000` |

Nginx defaults to `backend:8000` for Compose, validates host/port, uses the
container's private DNS resolver, and refreshes resolution every 10 seconds.
`/api/` continues to strip one prefix. React receives no provider/database keys.
API proxy responses include `Cache-Control: no-store`. Do not add a Cloudflare
cache-everything rule; bypass `/api/*` and all authenticated responses.

Collector only:

| Variable | Initial value / policy |
| --- | --- |
| `RAILWAY_RUN_UID` | `0` **only on collector**, to initialize its root-owned Railway volume |
| `COLLECTOR_SNAPSHOT_DIR` | `/app/collector-data` |
| `COLLECTOR_RAW_DATA_DIR` | `/app/collector-data/raw` |
| `DISCOVERY_ENABLED` | `true` only when intentionally starting the worker |
| `COLLECTION_ALLOW_LIVE` | `false` until credential and source permission verification |
| `BRABBLE_API_KEY` | Unset until authorized provider credentials are supplied |

The collector bootstrap changes only the fixed mount directory owner, then drops
groups/GID/UID to 10001 before executing discovery. It never recursively changes
user files. Backend and frontend keep their existing non-root Docker users.
Railway volumes cannot be shared across independently deployed services; only
collector mounts this volume. Candidate metadata is stored in PostgreSQL; raw
snapshots remain collector-owned evidence. Enable only one collector replica.
Do not delete or replace an existing evidence volume to resolve a permission error.

The underlying supported command is
`python -m workers.discovery --watch --allow-live`. The wrapper adds `--allow-live`
only for explicit `COLLECTION_ALLOW_LIVE=true`. This does not override registered
source permissions, robots/terms approval, quotas, review or publication gates.
Missing Brabble credentials currently block live acquisition. Candidate records
must still receive human review; no automatic approval/publication is added.
Public ML predictions and outbound email remain disabled.

## GitHub deployment governance

Use the existing `CI` workflow: PR validation already targets `develop` and `main`,
including backend/frontend tests, Module 2.4, Docker builds and disposable
PostgreSQL/browser acceptance. Do not add a parallel workflow doing the same work.
For staging, connect only this feature branch to the staging environment. For
production, connect only `main`, enable Railway **Wait for CI**, and protect main
with required CI checks and owner review. Confirm these provider/GitHub settings
before enabling auto-deploy; they cannot be asserted from this repository alone.
Use separate frontend/backend/collector services and provider deployment alerts.

## Data and backup boundary

The new database is empty until migrations and an explicitly reviewed import run.
The local 1,362 institutions and five catalog events are **not** copied by this
deployment. Do not upload the local database wholesale: it contains user/private
and review data. Preserve IDs/attribution through a separately reviewed export and
import, reject unapproved candidates, and verify duplicate handling first.
Keep provider volume backups enabled. Before any production import or schema
change, take an access-controlled `pg_dump` backup and restore into a separate
disposable database; verify migration revision and counts there. Provider backup
configuration and restore are not verified until provider access exists.

## Public verification and Cloudflare

1. Deploy staging, wait for the migration release phase, and verify `/api/ready`
   through the **actual generated frontend domain**. Confirm database revision,
   frontend routing refresh, authentication/logout, saved events, catalog and
   university queries. Empty data is expected until reviewed imports are approved.
2. Verify the collector's unprivileged runtime and persistent evidence across a
   restart without enabling live collection. Verify SMTP and public ML stay off.
3. Only then add the owner-confirmed custom hostname to Railway. Read its exact
   CNAME/TXT verification records and edit only matching records in the confirmed
   Cloudflare zone. No hostname, CNAME destination or TXT value is pre-invented.
4. Verify domain ownership and certificate issuance before traffic cutover. Do
   not disable origin certificate verification to make a smoke test pass.
5. Railway's current Cloudflare guidance recommends Full rather than Full (strict)
   for its proxied-domain certificate behavior. This is a security tradeoff,
   not authorization to weaken a zone setting. Leave proxy/SSL changes pending
   actual certificate inspection and owner decision. Validate DNS-only origin TLS
   first where supported; do not assume Cloudflare proxy compatibility.
6. After approved DNS/proxy configuration, verify HTTPS, redirects, login/logout,
   saved events and API cache headers on the custom domain. Record real URLs and
   deployment IDs. Roll back only this hostname's records if verification fails.

Access still required: Railway account/project authorization and GitHub repository
connection; Cloudflare authorization for the specific owned zone and exact desired
hostname; authorized Brabble key/source policy for live acquisition. These values
must be supplied through provider secret stores, never in chat or commits.

References: [private networking](https://docs.railway.com/networking/private-networking),
[domains](https://docs.railway.com/networking/domains/working-with-domains),
[volumes](https://docs.railway.com/volumes),
[health checks](https://docs.railway.com/deployments/healthchecks),
[pre-deploy phase](https://docs.railway.com/deployments/pre-deploy-command),
[configuration reference](https://docs.railway.com/config-as-code/reference).
