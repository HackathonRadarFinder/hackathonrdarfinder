"""v4.1 acceptance tests for hackathon auto-publishing, reason codes, and idempotency."""
from __future__ import annotations

import importlib
import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.hackathon import Hackathon
from app.models.organization import Organization
from app.services.scraper_ingestion import ingest_events


def _load_optional(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        return None


@pytest.fixture(params=["sqlite", "postgres"])
def db_engine(request, tmp_path):
    if request.param == "sqlite":
        url = f"sqlite+pysqlite:///{(tmp_path / 'autopublish_v41.db').as_posix()}"
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


def _valid_hackathon_payload(suffix: str = "1") -> dict:
    now = datetime.now(timezone.utc)
    return {
        "title": f"India AI Radar Hack {suffix}",
        "organization": "Radar Builders Collective",
        "url": f"https://unstop.com/hackathons/radar-v41-{suffix}",
        "source": "Unstop",
        "mode": "Online",
        "location": "Online",
        "start_date": (now + timedelta(days=5)).isoformat(),
        "end_date": (now + timedelta(days=7)).isoformat(),
        "registration_deadline": (now + timedelta(days=4)).isoformat(),
        "scraped_at": now.isoformat(),
        "description": "Complete v4.1 hackathon record with source and dates.",
    }


def _evaluate_quality_gate(payload: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not (payload.get("title") or "").strip():
        reasons.append("MISSING_TITLE")
    if not (payload.get("organization") or "").strip():
        reasons.append("MISSING_ORGANIZATION")
    url = (payload.get("url") or "").strip()
    if not url.startswith("https://"):
        reasons.append("INVALID_SOURCE_URL")
    if not payload.get("start_date") or not payload.get("end_date"):
        reasons.append("MISSING_EVENT_DATES")
    if not (payload.get("source") or "").strip():
        reasons.append("MISSING_SOURCE")
    return (len(reasons) == 0), reasons


def test_valid_hackathon_autopublishes(db_engine):
    ingestion_mod = _load_optional("app.services.scraper_ingestion")
    payload = _valid_hackathon_payload("autopub-valid")
    published, reasons = _evaluate_quality_gate(payload)
    assert published is True
    assert reasons == []

    if hasattr(ingestion_mod, "evaluate_and_publish"):
        with Session(db_engine) as session:
            out = ingestion_mod.evaluate_and_publish(session, payload)
            assert out.get("published") is True
            assert out.get("reason_codes", []) == []

    with Session(db_engine) as session:
        res = ingest_events(session, [payload])
        session.commit()
        assert res.inserted == 1
        row = session.scalar(select(Hackathon).where(Hackathon.url == payload["url"]))
        assert row is not None
        assert row.title == payload["title"]


def test_incomplete_hackathon_stays_unpublished_with_reason_codes():
    incomplete = {
        "title": "",
        "organization": "",
        "url": "http://insecure.example.com/hack",
        "source": "Unstop",
    }
    published, reasons = _evaluate_quality_gate(incomplete)
    assert published is False
    assert "MISSING_TITLE" in reasons
    assert "MISSING_ORGANIZATION" in reasons
    assert "INVALID_SOURCE_URL" in reasons
    assert "MISSING_EVENT_DATES" in reasons


def test_idempotent_recollection_updates_without_duplicating(db_engine):
    first = _valid_hackathon_payload("idem-1")
    second = dict(first, title="India AI Radar Hack idem-1 (Updated Edition)")

    with Session(db_engine) as session:
        first_res = ingest_events(session, [first])
        session.commit()
        assert first_res.inserted == 1

        dup_res = ingest_events(session, [second])
        session.commit()
        assert dup_res.duplicates == 1

        total_events = session.scalar(select(func.count()).select_from(Hackathon))
        total_orgs = session.scalar(select(func.count()).select_from(Organization))
        assert total_events == 1
        assert total_orgs == 1


def test_distinct_editions_are_not_falsely_merged_and_preserve_provenance(db_engine):
    edition_2026 = _valid_hackathon_payload("edition-2026")
    edition_2027 = dict(
        _valid_hackathon_payload("edition-2027"),
        title="India AI Radar Hack 2027 Edition",
        url="https://unstop.com/hackathons/radar-v41-edition-2027",
    )

    with Session(db_engine) as session:
        res = ingest_events(session, [edition_2026, edition_2027])
        session.commit()
        assert res.inserted == 2
        assert res.duplicates == 0
        rows = session.scalars(select(Hackathon).order_by(Hackathon.id)).all()
        assert len(rows) == 2
        assert all(row.source == "Unstop" and row.url.startswith("https://") for row in rows)
