# Free Render demo: Hackathon Radar Finder

> **Demo only — no services have been provisioned yet.** Blueprint in
> `render.staging.yaml` uses only Free Render web services and a Free
> PostgreSQL instance. This is not a durable production architecture.

## What the Free tier really means

- Two Free **public** web services: FastAPI (8000) and React/Nginx (8080).
- One Free **private-network** PostgreSQL database (1 GB, at most one per
  workspace, expires after **30 days**, no managed backups).
- Web instances sleep after 15 minutes without inbound traffic; first load
  may take about a minute. There is no persistent disk, background worker,
  scheduled job, shell or paid pre-deploy phase.
- The web frontend must reach the Free backend through the backend's
  **public HTTPS hostname**. Free web services do not receive Render private
  network connections. Nginx verifies the upstream certificate and proxies
  `/api/*` same-origin. Do not switch the backend to plain HTTP or disable
  certificate verification.
- Shared Free instance-hour and other usage limits can suspend the demo.
  Keep a separate backup of any data you want to retain. Nothing in this
  Blueprint migrates the user's local database.

Sources: https://render.com/docs/free,
https://render.com/docs/deploys,
https://render.com/docs/blueprint-spec.

## How to deploy without a bill

1. Review [PR #103](https://github.com/HackathonRadarFinder/hackathonrdarfinder/pull/103)
   and merge into `develop` only after its CI and review pass.
2. Open https://dashboard.render.com/ and select **New > Blueprint**.
3. Connect the repository `HackathonRadarFinder/hackathonrdarfinder`,
   choose **develop** and specify `render.staging.yaml` as the Blueprint path.
   Ensure it displays **two Free web services and one Free Postgres** before
   approving creation. **Do not accept an upgraded or paid tier.**
4. The backend image runs `python -m workers.migrate` on startup before
   Uvicorn (there is no Free pre-deploy phase). Advisory locking makes the
   migration step safe against concurrent migrations. Verify the build and
   deployment logs, and check the backend's public `/ready` endpoint.
5. Check that the frontend's `BACKEND_HOST` resolves to the actual
   `RENDER_EXTERNAL_HOSTNAME` of `hackathon-radar-demo-api`. If Render's
   cross-service reference is not populated, fix it in the Render dashboard
   with **just the backend hostname**, not an https:// URL, port or secret.
   `BACKEND_SCHEME=https`, `BACKEND_PORT=443`.
6. Verify the frontend's own `/health` and its public `/api/ready`.
   The API proxy may be slow on first request while the backend wakes.
   Check login/logout, search, filters, saved events and college browsing.
   A fresh database has no seeded catalog or institution records.

## Collector

The free demo **does not run** the collector. Render free instances lack
persistent disk and always-running background workers. Live Brabble collection
is also blocked by missing authorized provider credentials and human review.
Do not attempt a fake six-hour schedule using an HTTP ping or an ephemeral
worker process. The collector remains implemented in the repository for a
future durable deployment.

## Database and credentials

`DATABASE_URL` is injected from the Free database's **internal URL** and
normalized to the psycopg SQLAlchemy driver by the existing backend settings.
`SECRET_KEY` is generated privately by Render. SMTP is disabled. Never
paste credentials, import old local users, or commit production .env files.

The new Free database has no backups and will expire after 30 days. If data
matters, plan and verify independent export/restore **before** its expiration.
Do not import the 1,362 institutions, five catalog events or local PostgreSQL
dump without a separate reviewed and privacy-safe import process.

## Cloudflare

First verify the Render-generated URLs. Adding a custom domain through
Cloudflare is **optional** for the demo. If you do, use the exact records
supplied by Render for the owner-controlled hostname. Preserve existing DNS;
avoid caching `/api/*` or authenticated requests. No DNS changes have been
made.

## Exit criteria

The free demo is usable when the actual frontend HTTPS URL shows the app,
`/api/ready` responds, database migrations are current, login works and
catalog filters perform as expected (even when the fresh catalog is empty).
Report **demo deployed**, not **production deployed**. Upgrade hosting and
replace the expiring database only after separate approval.
