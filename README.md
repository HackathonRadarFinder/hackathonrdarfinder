# Hackathon Radar Finder

React/Vite frontend, FastAPI backend and PostgreSQL 16 for governed event discovery, review, saved events and explainable recommendations.

## Local setup

Use Python 3.12, Node 24 and Docker Desktop. From this release worktree:

```powershell
Copy-Item backend/.env.example backend/.env
# Set independent local secrets and matching PostgreSQL credentials in backend/.env.
docker compose -p hackathonradarfinder up -d --build
```

For an existing installation, preserve backend/.env and the PostgreSQL volume. Back up before migrations; do not run volume reset commands. Compose runs the migration service before starting the backend. `/ready` requires current migrations.

- Frontend: http://127.0.0.1:5173
- API: http://127.0.0.1:8000/docs
- Proxied readiness: http://127.0.0.1:5173/api/ready

Register an ordinary account through React. Existing administrator roles are checked from the database on every protected operation. Public registration cannot assign privileged roles. Administrator provisioning must use the existing authorized database administration process; no default admin password is shipped.

The administrator Sources tab supports CSV/XLSX uploads into a review queue. Register a current, permission-backed source first; upload with its exact approval reference. Approvals publish events; imports alone do not. Duplicate merges retain snapshots and provenance. Annual editions sharing a landing URL require explicit review or edition-specific URLs.

```powershell
# Optional in-app reminder scheduler. No SMTP transport is used.
docker compose -p hackathonradarfinder --profile workers up -d in-app-reminders
# Safe email dry-run: no delivery or claims.
docker compose -p hackathonradarfinder run --rm --no-deps -e EMAIL_MODE=dry-run backend python -m workers.email_reminders
```

Live collection stays disabled unless explicitly configured with valid source permission, robots approval and `DISCOVERY_ENABLED=true`. Run `python -m workers.discovery --watch` in an authorized worker environment; `--allow-live` remains separately required. See [India discovery](docs/operations/INDIA-DISCOVERY.md).

## Validation and release status

See [FINAL_RELEASE_REPORT.md](FINAL_RELEASE_REPORT.md) for verified counts, commands, limitations and deployment guidance. [RELEASE_CHECKPOINT.md](RELEASE_CHECKPOINT.md) records exact follow-up actions. See [DEMO_CHECKLIST.md](DEMO_CHECKLIST.md) for startup and fixture demonstrations and [REMAINING_BLOCKERS.md](REMAINING_BLOCKERS.md) for external dependencies. Public university browsing is at `/universities`; signed-in Preferences includes display-name editing. Source-backed stored facts can be stale; check organizer pages. Public ML forecasts remain withheld until temporal evidence and calibration support them.
