# Hackathon Radar Finder – Source Registry

## Overview

A FastAPI backend for managing hackathon and event data sources such as Unstop and Devfolio.

## Tech Stack

- Python 3.11
- FastAPI
- SQLite
- SQLAlchemy
- Pytest

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run the Application

```powershell
python -m uvicorn app.main:app --reload
```

API: <http://127.0.0.1:8000>

Swagger documentation: <http://127.0.0.1:8000/docs>

## API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/sources` | Create a source |
| GET | `/sources` | List sources |
| GET | `/sources?active_only=true` | List active sources |
| GET | `/sources/{source_id}` | Get a source |
| PUT | `/sources/{source_id}` | Update a source |
| PUT | `/sources/{source_id}/pause` | Pause a source |
| PUT | `/sources/{source_id}/resume` | Resume a source |
| PATCH | `/sources/{source_id}/crawl` | Update crawl timestamp |
| DELETE | `/sources/{source_id}` | Delete a source |

## Collector Integration

The Collector retrieves active sources using `GET /sources?active_only=true` and updates the crawl timestamp using `PATCH /sources/{source_id}/crawl`.

## Run Tests

```powershell
python -m pytest -v
```

Expected result: 11 tests passed.
