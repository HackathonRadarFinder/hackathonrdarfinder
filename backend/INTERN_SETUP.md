# Hackathon Radar Finder - Intern Setup Guide

## 1. Clone the Repository

git clone https://github.com/HackathonRadarFinder/hackathonrdarfinder.git
cd hackathonrdarfinder

## 2. Switch to Develop Branch

git checkout develop
git pull origin develop

## 3. Backend Setup

cd backend

python -m venv .venv

.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

## 4. Run the Backend

python -m uvicorn app.main:app --reload

Backend URL:

http://127.0.0.1:8000

Swagger API Documentation:

http://127.0.0.1:8000/docs

Health Check:

http://127.0.0.1:8000/health

Expected Response:

{
  "status": "healthy",
  "service": "hackathon-radar-api",
  "version": "0.1.0"
}

## 5. Branch Rules

Do not work directly on:

- main
- develop

Always create a feature branch from develop.

Example:

git checkout develop
git pull origin develop
git checkout -b feature/BE-001-events-api

Branch naming examples:

feature/BE-001-events-api
feature/DB-001-postgresql
feature/SCR-001-devpost
feature/AI-001-prediction-model
feature/FE-001-dashboard
fix/BE-001-api-error

## 6. Folder Ownership

Backend APIs:

backend/app/api/routes/

Schemas:

backend/app/schemas/

Database Models:

backend/app/models/

Core Configuration:

backend/app/core/

Business Logic:

backend/app/services/

Scrapers:

backend/scraper/

AI / Prediction:

backend/ai/

Data Processing:

backend/data/

Tests:

backend/tests/

Frontend:

frontend/

Infrastructure / Deployment:

infrastructure/

## 7. Current Backend APIs

Events:

GET /events/
POST /events/
GET /events/{event_id}
PUT /events/{event_id}
DELETE /events/{event_id}

Organizations:

GET /organizations/
POST /organizations/
GET /organizations/{organization_id}
PUT /organizations/{organization_id}
DELETE /organizations/{organization_id}

Other Base Routes:

GET /predictions/
GET /auth/status
GET /notifications/
GET /health

## 8. Standard Hackathon Data Format

All scraper and backend teams must use the same fields:

{
  "title": "",
  "organization": "",
  "start_date": null,
  "end_date": null,
  "registration_deadline": null,
  "location": "",
  "mode": "",
  "prize": "",
  "description": "",
  "url": "",
  "source": "",
  "scraped_at": null
}

Do not rename these fields without approval.

## 9. Before Creating a Pull Request

Make sure:

- Your code runs locally
- Backend starts without errors
- Swagger loads correctly if working on APIs
- Only files related to your task are changed
- No .env file is committed
- No virtual environment is committed
- No local database file is committed

## 10. Pull Request Rules

Push your branch:

git add .
git commit -m "feat: short description of task"
git push -u origin your-branch-name

Then create a Pull Request into:

develop

PR must include:

- Task completed
- Files changed
- Testing performed
- Screenshot/API output
- Related GitHub issue number

Do not merge your own PR unless approved.

## 11. Important Rules

- Never push directly to main
- Never push directly to develop
- Do not change shared schemas without approval
- Do not change database structure without approval
- Do not rename common API fields
- Pull latest develop before starting work
- Keep commits task-specific

