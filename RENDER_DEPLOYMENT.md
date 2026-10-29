# Render staging deployment (opt-in)

Status: Blueprint prepared for review. **No Render resources, spend, public URL, or
Cloudflare changes were created by this GitHub change.** Only deploy after reviewing
the cost estimate and permissions in your own Render workspace.

## 1. Review costs and create the Blueprint

Use [Render Dashboard](https://dashboard.render.com/) > **New > Blueprint**.
Connect GitHub `HackathonRadarFinder/hackathonrdarfinder`, select branch
`develop`, and set Blueprint filename to **`render.staging.yaml`**.
Do not select the existing production `main` branch for this staging Blueprint.

The Blueprint defines a **paid** private FastAPI service (starter-sized
compute), a **paid** PostgreSQL instance, and a **free** frontend web service.
All resources use Singapore; auto-deploys are OFF to prevent unexpected
redeploys. Render will show a cost estimate. **Do not approve creation or
billing unless the owner accepts it.**

Important: Render free web instances can sleep; free Postgres expires after
30 days, which is why this file intentionally uses paid, persistent Postgres.
The Blueprint never imports the local database or enables source scraping.

## 2. Verify startup

The API uses `backend/Dockerfile`, listens at `0.0.0.0:8000` and runs
`python -m workers.migrate` before deploy. It is a Render private service,
not publicly exposed. The Render PostgreSQL internal URL is passed through
`DATABASE_URL`. Existing config normalizes `postgresql://` into the installed
SQLAlchemy psycopg driver. The `SECRET_KEY` is generated in Render; do not
paste it into the repository or chat.

The frontend uses `frontend/Dockerfile` and Nginx port 8080. The Blueprint
injects the actual private backend hostname using a Render service reference.
The frontend is the only public web service.

After deployment, open the **actual** Render-generated HTTPS frontend URL and
check `/health`, then `/api/ready`. An empty catalog/university directory is
expected until a separate, reviewed import is approved.

Test page refresh, registration/login/logout, saved events, catalog filters,
university search, and browser console/network errors. Check API startup
logs for migration success. Do not claim health from build status alone.

## 3. Collector — second stage after staging works

Do not provision the worker before the API and database are healthy. For the
collector, Render requires a **paid background worker** and a **persistent
disk** mounted at `/app/collector-data` (one replica). Reuse the backend
Dockerfile and the existing collector wrapper. Verify filesystem permissions
for UID 10001 on the mounted disk; **never delete an existing evidence disk**
to fix permissions.

Environment: `DATABASE_URL` from the same private Render Postgres,
`SECRET_KEY` set in Render, `ENVIRONMENT=staging`, `DEBUG=false`,
`EMAIL_MODE=disabled`, `COLLECTOR_SNAPSHOT_DIR=/app/collector-data`,
`COLLECTOR_RAW_DATA_DIR=/app/collector-data/raw`,
`COLLECTION_ALLOW_LIVE=false`. Start with no authorized live sources;
enable collection only after source permissions, quota and credentials
are verified. Never auto-approve candidates or publish unreviewed records.

The current wrapper is named `workers.railway_collector` for historical
reasons; do not change privileges, service wiring or startup command without
validating the disk behavior on Render.

## 4. Data and production isolation

Staging starts with a separate database. Existing local data (1,362
institutions, five published catalog events, users and saved items) is
**not** copied. Never import the entire local PostgreSQL dump containing
private user data. Plan a narrowly scoped and reviewed data export/import
with original IDs and attribution, plus duplicate checks and a backup.

Keep `main` untouched until staging passes owner review. Production
requires a separate persistent database, provider backup policy, paid plan
review, monitoring/alerts, and a release PR.

## 5. Cloudflare after the Render URL works

Do not change Cloudflare DNS before a staging URL has been verified.
When the owner confirms the exact hostname, add it in Render's custom-domain
settings and copy the **actual** DNS records Render supplies. Change only
the corresponding DNS records in the owner's Cloudflare zone. Start DNS-only
while validating Render's TLS, and check end-to-end HTTPS before changing any
Cloudflare proxy behavior. Never cache `/api/*` or authenticated responses.
