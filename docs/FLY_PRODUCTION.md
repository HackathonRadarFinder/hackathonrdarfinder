# Existing Fly app deployment

App: `hackathonrdarfinder`, region: `sin`. Do not create another app.

## Required operator input

Use an existing Supabase project. From its Connect dialog select Session pooler
(port 5432). Set `DATABASE_URL` in Fly secrets with this shape:

```text
postgresql+psycopg://postgres.PROJECT_REF:URL_ENCODED_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require
```

Use the actual host from Supabase; percent-encode special password characters.
Do not commit a real URI or put it in command history. Import secrets via stdin.
The required secret names are DATABASE_URL, SECRET_KEY (random, at least 32
characters), ENVIRONMENT=production, DEBUG=false, and EMAIL_MODE=disabled.
Stage them with `fly secrets import --stage -a hackathonrdarfinder`.

Fly usage can incur charges. Confirm account allowance or obtain billing approval
before deploying. No database reset, downgrade, seed, or collector run is required.

## Release

From `backend`, validate with `fly config validate`.
Reuse the existing uploaded image when only configuration changed:

```sh
fly deploy --app hackathonrdarfinder --image registry.fly.io/hackathonrdarfinder@sha256:6c54871d8a876ba08d1ecc742aaf69e083484615770372c7d6386d631adeb334 --ha=false
```

The release command runs `alembic upgrade head`. Do not skip a failed migration.
Check release logs, `/health`, `/ready`, `/auth/status`, and catalog endpoints.
`/ready` verifies database connectivity and that all migration heads are applied.
Existing data must be checked before claiming preservation or catalog success.
The web command starts only Uvicorn: no collector or notification scheduler is
started. Email stays disabled. Do not launch worker commands without approval.

## Frontend

The `frontend/netlify.toml` file prepares a static Netlify deployment. Select
`frontend` as the base directory, and leave VITE_API_BASE_URL unset (defaults to
`/api`). Its API proxy forwards to the Fly backend, preserving the existing
Nginx path behavior, and its fallback supports React Router deep links.
No browser CORS exception is needed because requests are same-origin.
The existing Nginx configuration uses Docker Compose hostname `backend` and
should only be used where that hostname resolves to the backend service.

Check the hosting account's free limits before publishing. Do not enable an
automatic paid upgrade. Once both services are live, verify registration,
login/logout, catalog/filter/detail views, and saved events using a dedicated
test account. Do not claim these flows passed from a build alone.
