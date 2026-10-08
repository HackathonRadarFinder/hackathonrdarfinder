# Running the Application Manual

This guide explains how to run the Hackathon Radar application locally for development, validation, and team onboarding.

---

## 1. Prerequisites

Before you start, make sure these are installed on your machine:

- Python 3.12+
- Node.js 20+
- npm
- Docker Desktop or Docker Engine
- Git
- A terminal such as PowerShell, Git Bash, or WSL

For Docker on Windows, Docker Desktop should be running before starting the project.

---

## 2. Clone the repository

```bash
git clone <repo-url>
cd HackathonRadarFinder/hackathonrdarfinder
```

---

## 3. Running with Docker Compose (recommended)

This is the simplest way to start the full stack.

### Start the app
```bash
docker compose up -d --build
```

### Check containers
```bash
docker compose ps
```

### View logs
```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db
```

### Stop the app
```bash
docker compose down
```

### Stop and remove volumes
```bash
docker compose down -v
```

---

## 4. Default service URLs

Once the stack is running:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Health check: http://localhost:8000/health
- PostgreSQL: localhost:5432

---

## 5. Backend manual run

If you want to run the backend outside Docker:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Then configure environment values if needed:

```bash
copy .env.example .env
```

Then start the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

To test health:

```bash
curl http://localhost:8000/health
```

---

## 6. Frontend manual run

```bash
cd frontend
npm install
npm run dev
```

The frontend should start in dev mode and use the Vite dev server.

---

## 7. Backend tests

```bash
cd backend
python -m pytest -q
```

---

## 8. Frontend validation

```bash
cd frontend
npm ci
npm run lint
npm run build
```

---

## 9. Troubleshooting

### Docker Desktop not starting
- Check that Docker Desktop is running
- Ensure WSL is healthy
- Confirm free disk space is available
- Restart Docker Desktop if the engine is not responding

### Database connection issues
- Verify Postgres container is running
- Confirm `.env` values match the service configuration
- Run:

```bash
docker exec -it <db-container-name> pg_isready -U postgres -d hackathon_radar
```

### Backend fails to start
- Validate Python dependencies are installed
- Confirm required environment variables exist
- Check the API logs:

```bash
docker compose logs -f backend
```

### Frontend fails to load
- Ensure Node dependencies are installed
- Verify the Vite dev server started correctly
- Check the frontend container logs if using Docker mode

---

## 10. Team onboarding checklist

Use this before beginning work:

- [ ] Install Python 3.12
- [ ] Install Node.js 20
- [ ] Install Docker Desktop
- [ ] Clone repository
- [ ] Start Docker Desktop
- [ ] Run `docker compose up -d --build`
- [ ] Verify API health at `http://localhost:8000/health`
- [ ] Open the frontend at `http://localhost:5173`
- [ ] Run tests before submitting changes

---

## 11. Useful commands summary

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f
docker compose down
docker compose down -v
python -m pytest -q
npm run dev
npm run build
```

This setup is intended to make onboarding and local validation straightforward for the whole team.
