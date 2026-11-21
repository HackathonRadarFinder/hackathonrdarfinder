"""INT-05 analytics summary: counts, freshness, and honest 'unavailable' states."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.hackathon import Hackathon
from app.models.institution import Institution


def naive_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


@pytest.fixture
def client(session):
    app.dependency_overrides[get_db] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


def add_college(db, n):
    db.add(Institution(identifier=f"AISHE-{n}", name=f"College {n}", state="Rajasthan",
                       category="College", provenance={}, last_verified_at=naive_now()))


def test_empty_database_reports_zeros_and_unavailable_not_guesses(client):
    body = client.get("/analytics/summary").json()
    assert body["hackathons_total"] == 0
    assert body["indexed_colleges"] == 0
    assert body["active_jobs_14d"]["value"] is None
    assert body["active_jobs_14d"]["status"] == "unavailable"
    assert body["hackathons_by_category"] is None
    assert body["hackathons_by_category_status"] == "unavailable_until_category_migration"
    assert body["freshness"]["status"] == "no_collection_data"
    assert body["freshness"]["latest_hackathon_collected_at"] is None


def test_counts_upcoming_colleges_and_freshness(client, session):
    now = naive_now()
    session.add_all([
        Hackathon(title="Upcoming", start_date=now + timedelta(days=10), scraped_at=now - timedelta(hours=2)),
        Hackathon(title="Past recent", start_date=now - timedelta(days=5), scraped_at=now - timedelta(days=3)),
        Hackathon(title="Past old", start_date=now - timedelta(days=400), scraped_at=now - timedelta(days=60)),
    ])
    for n in range(4):
        add_college(session, n)
    session.commit()
    body = client.get("/analytics/summary").json()
    assert body["hackathons_total"] == 3
    assert body["hackathons_upcoming"] == 1
    assert body["indexed_colleges"] == 4
    assert body["freshness"]["hackathons_collected_last_24h"] == 1
    assert body["freshness"]["hackathons_collected_last_7d"] == 2
    assert body["freshness"]["status"] == "available"


def test_jobs_table_without_timestamp_column_stays_unavailable(client, session):
    session.execute(text("CREATE TABLE jobs (id INTEGER PRIMARY KEY, title TEXT)"))
    session.commit()
    jobs = client.get("/analytics/summary").json()["active_jobs_14d"]
    assert jobs["value"] is None and jobs["status"] == "unavailable"


def test_jobs_use_14_day_window_and_closing_date(client, session):
    now = naive_now()
    session.execute(text("CREATE TABLE jobs (id INTEGER PRIMARY KEY, first_published_at DATETIME, closes_at DATETIME)"))
    rows = [
        (now - timedelta(days=1), None),                       # active
        (now - timedelta(days=13), now + timedelta(days=5)),   # active
        (now - timedelta(days=15), None),                      # older than 14 days
        (now - timedelta(days=2), now - timedelta(days=1)),    # already closed
    ]
    for published, closes in rows:
        session.execute(text("INSERT INTO jobs (first_published_at, closes_at) VALUES (:p, :c)"),
                        {"p": published, "c": closes})
    session.commit()
    jobs = client.get("/analytics/summary").json()["active_jobs_14d"]
    assert jobs == {"value": 2, "status": "available", "reason": None}


def test_category_breakdown_when_column_exists(client, session):
    session.execute(text("ALTER TABLE hackathons ADD COLUMN category VARCHAR(50)"))
    for title, category in [("a", "college"), ("b", "college"), ("c", "startup"), ("d", None)]:
        session.execute(text("INSERT INTO hackathons (title, category) VALUES (:t, :c)"),
                        {"t": title, "c": category})
    session.commit()
    body = client.get("/analytics/summary").json()
    assert body["hackathons_by_category_status"] == "available"
    assert body["hackathons_by_category"] == {"college": 2, "startup": 1, "unknown": 1}


def test_category_counts_only_live_hackathons(client, session):
    now = naive_now()
    session.execute(text("ALTER TABLE hackathons ADD COLUMN category VARCHAR(50)"))
    for title, category, end in [("live", "college", now + timedelta(days=3)),
                                 ("no end date", "college", None),
                                 ("ended", "college", now - timedelta(days=3))]:
        session.execute(text("INSERT INTO hackathons (title, category, end_date) VALUES (:t, :c, :e)"),
                        {"t": title, "c": category, "e": end})
    session.commit()
    body = client.get("/analytics").json()
    assert body["hackathons_total"] == 3
    assert body["hackathons_live"] == 2
    assert body["hackathons_by_category"] == {"college": 2}


def test_ingest_runs_freshness_uses_only_successful_runs(client, session):
    session.execute(text("CREATE TABLE ingest_runs (id INTEGER PRIMARY KEY, area TEXT, status TEXT, finished_at DATETIME)"))
    rows = [("hackathons", "success", "2026-11-01 10:00:00"), ("hackathons", "success", "2026-11-02 10:00:00"),
            ("hackathons", "failed", "2026-11-03 10:00:00"), ("jobs", "failed", "2026-11-03 11:00:00")]
    for area, status, finished in rows:
        session.execute(text("INSERT INTO ingest_runs (area, status, finished_at) VALUES (:a, :s, :f)"),
                        {"a": area, "s": status, "f": finished})
    session.commit()
    fresh = client.get("/analytics").json()["freshness"]
    assert fresh["ingest_runs_status"] == "available"
    assert list(fresh["last_successful_ingest_by_area"]) == ["hackathons"]
    assert fresh["last_successful_ingest_by_area"]["hackathons"].startswith("2026-11-02T10:00:00")


def test_no_ingest_runs_table_is_reported_unavailable(client):
    fresh = client.get("/analytics").json()["freshness"]
    assert fresh["last_successful_ingest_by_area"] is None
    assert fresh["ingest_runs_status"] == "unavailable_until_ingest_runs_migration"
