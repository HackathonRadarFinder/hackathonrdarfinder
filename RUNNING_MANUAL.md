# Local running and validation

Use Python 3.12, Node 24, and a running Docker engine. Existing databases and
backend/.env must be preserved. If backend/.env does not exist, create it from
backend/.env.example and replace credential placeholders with generated values.
Compose loads backend/.env; DATABASE_URL must address db:5432 within Docker.
For a host-run backend, use the appropriate host/database connection separately.
Never overwrite a populated environment file or publish its contents.

With explicit approval to start the local application stack:

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Frontend: http://localhost:5173; backend: http://localhost:8000;
health: /health and /api/v1/health; PostgreSQL host port: 127.0.0.1:5433.
The existing radar_postgres_data named volume is retained. Do not use down -v.
The frontend Nginx server listens internally on 8080 and proxies /api/ to the
backend, removing only that prefix. The current frontend auth service is still
mocked; wiring it to /api/auth is a separate task.

Schema migration is an explicit operator step, never an automatic API startup
operation. Run against only the reviewed target after backup and approval.
No schema changes are needed merely to validate the local test suite.

Backend validation with the existing virtual environment:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m pip check
```

The tests supply isolated settings and temporary databases. Use python -m pytest
so the backend package is importable. The separate source-registry module has
its own app package and database side effects; do not combine its suite with
the main backend suite without isolation.

Frontend validation with installed dependencies:

```bash
cd frontend
npm run lint
npm run build
```

Only on a fresh checkout with no dependencies use npm ci. It replaces
node_modules; do not run it over another developer's active dependency work.
See docs/operations/OPS-001-INTEGRATION-REVIEW.md for validation limits.
