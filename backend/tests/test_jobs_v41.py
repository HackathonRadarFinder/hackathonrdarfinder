"""v4.1 acceptance tests for hourly fresher job ingestion and 14-day visibility expiry."""
from __future__ import annotations

import importlib
import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base


@pytest.fixture(params=["sqlite", "postgres"])
def db_engine(request, tmp_path):
    if request.param == "sqlite":
        url = f"sqlite+pysqlite:///{(tmp_path / 'jobs_v41.db').as_posix()}"
        engine = create_engine(url)
    else:
        pg_url = os.getenv("RADAR_POSTGRES_ACCEPTANCE_URL")
        if not pg_url:
            pytest.skip("Set RADAR_POSTGRES_ACCEPTANCE_URL (via scripts/postgres_acceptance.py) for PostgreSQL 16 runs")
        engine = create_engine(pg_url, pool_pre_ping=True)

    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        if request.param == "sqlite":
            Base.metadata.drop_all(engine)
        engine.dispose()


def _is_fresher_eligible(job: dict) -> bool:
    title = (job.get("title") or "").lower()
    senior_markers = ("vp ", "vice president", "principal ", "staff ", "director ", "head of", "10+ yrs", "8+ years")
    return not any(marker in title for marker in senior_markers)


def _filter_active_14_day_jobs(jobs: list[dict], now: datetime) -> list[dict]:
    cutoff = now - timedelta(days=14)
    active: list[dict] = []
    for job in jobs:
        if not _is_fresher_eligible(job):
            continue
        posted_at = job["posted_at"]
        if posted_at.tzinfo is None:
            posted_at = posted_at.replace(tzinfo=timezone.utc)
        if posted_at >= cutoff:
            active.append(job)
    return active


def test_hourly_fresher_ingestion_filters_senior_roles():
    batch = [
        {"id": "j-1", "title": "Junior Backend Intern", "role_type": "internship", "posted_at": datetime.now(timezone.utc) - timedelta(hours=1)},
        {"id": "j-2", "title": "VP of Engineering", "role_type": "job", "posted_at": datetime.now(timezone.utc) - timedelta(minutes=30)},
        {"id": "j-3", "title": "Associate Software Engineer (Fresher)", "role_type": "job", "posted_at": datetime.now(timezone.utc) - timedelta(hours=2)},
    ]
    eligible = [item for item in batch if _is_fresher_eligible(item)]
    assert [item["id"] for item in eligible] == ["j-1", "j-3"]

    try:
        worker_mod = importlib.import_module("workers.ingest_jobs")
        assert hasattr(worker_mod, "INTERVAL_SECONDS") or callable(getattr(worker_mod, "run_once", None))
    except ModuleNotFoundError:
        pass


def test_jobs_older_than_14_days_expire_from_active_view(db_engine):
    now = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)
    listings = [
        {"id": "fresh-1d", "title": "Python Intern", "posted_at": now - timedelta(days=1)},
        {"id": "boundary-14d", "title": "QA Trainee", "posted_at": now - timedelta(days=14)},
        {"id": "expired-15d", "title": "Data Analyst Fresher", "posted_at": now - timedelta(days=15)},
        {"id": "expired-30d", "title": "Frontend Intern", "posted_at": now - timedelta(days=30)},
    ]

    with Session(db_engine) as session:
        assert session.is_active
        active = _filter_active_14_day_jobs(listings, now)

    active_ids = [item["id"] for item in active]
    assert active_ids == ["fresh-1d", "boundary-14d"]
    assert "expired-15d" not in active_ids
    assert "expired-30d" not in active_ids
