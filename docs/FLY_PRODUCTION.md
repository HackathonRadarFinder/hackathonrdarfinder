# Fly.io-only production deployment

Target architecture:
- Existing FastAPI app: `hackathonrdarfinder` in `sin`.
- New React/Nginx app (proposed name): `hackathonrdarfinder-web` in `sin`.
- Fly Managed Postgres (MPG) cluster in `sin`, private to the same Fly organization.

No Render, Netlify, or Supabase is required. The frontend's same-origin
`/api/*` requests are proxied to `https://hackathonrdarfinder.fly.dev/*`.
Keep `VITE_API_BASE_URL` unset so it defaults to `/api`. The existing local
`frontend/Dockerfile`, `frontend/nginx.conf`, and Compose setup are unchanged.

**NOT DEPLOYED.** These are configuration and runbook changes only. Neither
a frontend app nor a database was provisioned by this change.

## 1. Check charges and existing infrastructure (before creating resources)

Fly bills by use. Managed Postgres Basic starts at **USD 38/month plus storage**;
backend/frontend Machines, storage, and data transfer may add charges. Fly is
not guaranteed free hosting. Get explicit billing approval and check the
account's allowances before creating paid resources. See
https://fly.io/pricing/ and https://fly.io/docs/mpg/.

```powershell
fly auth whoami
fly apps list
fly mpg list
```

Reuse the existing backend Fly app; do not create a duplicate backend. If
`hackathonrdarfinder-web` is already registered by someone else, choose an
available frontend name and change `frontend/fly.toml` accordingly. Never
delete existing database clusters or deployed apps to make room.

## 2. Review and merge the code before database attachment

The database adapter accepts Fly's `postgres://` and `postgresql://`
`DATABASE_URL` values by selecting the installed psycopg 3 driver. The Fly
backend release command is `alembic upgrade head`. It will not run safely
without the correct database secret and a production `SECRET_KEY`.

Make sure `SECRET_KEY` (minimum 32 random characters),
`ENVIRONMENT=production`, `DEBUG=false`, and `EMAIL_MODE=disabled` are
staged securely as Fly secrets. Use `fly secrets list -a hackathonrdarfinder`
to check **names only**; do not print or paste secret values. Do not put
credentials in source code, screenshots, logs, or shell history.

Confirm the migration head is still `e0f1a2b3c4d5` before deployment, and
take a verifiable backup if reusing a database containing any real data.

## 3. Create and attach Fly Managed Postgres (billable)

After explicit billing approval, create a cluster in the same Fly organization
and region as the backend. Review the selected plan and storage in the CLI
before confirming any charge:

```powershell
fly mpg create
fly mpg list
```

Only **after the backend code is ready**, attach the returned cluster ID:

```powershell
fly mpg attach <CLUSTER_ID> -a hackathonrdarfinder
```

Fly populates the `DATABASE_URL` secret automatically with a pooled URL; the
real URL does not need to be copied by the operator. **Important:** attaching
may trigger a deployment. Monitor it and never ignore a failed migration.

The fresh MPG cluster is **empty** until migrations create its tables; records
from any older SQLite/Postgres store are **not migrated automatically**.
Do not reset, drop, overwrite, or seed data without a reviewed backup and
explicit direction. Never enable collectors or email during deployment.

## 4. Deploy the existing backend app

From the repository root:

```powershell
cd backend
fly config validate
fly deploy -a hackathonrdarfinder --ha=false
fly status -a hackathonrdarfinder
fly logs -a hackathonrdarfinder
```

`backend/fly.toml` starts only the FastAPI web service, checks `/ready`, and
runs `alembic upgrade head` on release. It does not start a collector, scraper,
scheduled worker, or email delivery.

Check the following URLs **after** the backend is deployed:
- `https://hackathonrdarfinder.fly.dev/health`
- `https://hackathonrdarfinder.fly.dev/ready` (must report connected and current)
- `https://hackathonrdarfinder.fly.dev/auth/status`
- `https://hackathonrdarfinder.fly.dev/events/?page=1&page_size=5`

An empty but valid events page is not proof that legacy catalog data was
preserved. Verify the database contents separately before claiming success.

## 5. Create and deploy the Fly frontend app

Only after billing approval and the backend is healthy:

```powershell
cd ..\frontend
fly config validate
fly apps create hackathonrdarfinder-web
fly deploy -a hackathonrdarfinder-web --ha=false
fly status -a hackathonrdarfinder-web
fly logs -a hackathonrdarfinder-web
```

The frontend app uses `frontend/Dockerfile.fly` and
`frontend/nginx.fly.conf` (not the Compose Dockerfile or Nginx config).
It builds Vite static assets, serves React Router deep links, and proxies
`/api/events/` to the backend's `/events/` endpoint. This prevents browser
CORS problems by keeping the frontend's API calls on its own origin.

Validate:
- `https://hackathonrdarfinder-web.fly.dev/health`
- `https://hackathonrdarfinder-web.fly.dev/`
- `https://hackathonrdarfinder-web.fly.dev/api/ready`
- `https://hackathonrdarfinder-web.fly.dev/api/events/?page=1&page_size=5`
- A React Router deep link, browser refresh, register/login/logout,
  catalog/filter/details, saved events, and persistence across restart.

Use a dedicated test account. No live flows have been verified by this PR.
Do not enable scheduled discovery, external scraping, or email just because
the web application is reachable.

## Rollback and safety

If migrations fail, **stop** and inspect release logs. Do not bypass
`/ready`, downgrade/drop schemas, or point the app at a temporary database
to fake readiness. For existing data, preserve backups before migrations.
If the frontend proxy fails, check the Fly backend URL, DNS, and Nginx logs;
do not move to another hosting provider automatically.

Fly docs: https://fly.io/docs/mpg/ and https://fly.io/docs/about/pricing/
