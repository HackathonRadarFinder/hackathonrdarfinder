"""Offline adapter integration against disposable SQLite databases only."""
import json
import socket
from datetime import datetime

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.exceptions import AppException
from app.models.hackathon import Hackathon
from app.models.organization import Organization
from app.services.scraper_ingestion import ingest_events, normalize_unstop_collection

API_URL = "https://unstop.com/api/public/opportunity/search-result?page=1"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("ingestion must be offline")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)


def opportunity(**changes):
    return {"title": "Build a radar", "seo_url": "https://unstop.com/hackathons/radar-1",
            "organisation": {"name": "Builders"}, "region": "online",
            "details": "<p>Build <b>together</b></p>", "start_date": "2026-10-12T10:00:00+05:30",
            "end_date": "2026-10-13T10:00:00+05:30", **changes}


def envelope(items=None, **changes):
    return {"http_status": 200, "status": "success", "url": API_URL, "final_url": API_URL,
            "fetched_at": "2026-10-12T10:00:00+05:30",
            "raw_content": json.dumps({"data": {"data": items if items is not None else [opportunity()]}}),
            **changes}


def record(url="https://unstop.com/hackathons/radar-1", **changes):
    return {"title": "Build a radar", "organization": "Builders", "url": url,
            "source": "Unstop", "scraped_at": "2026-10-12T04:30:00Z", **changes}


@pytest.fixture(params=["memory", "file"])
def engine(request, tmp_path):
    url = "sqlite+pysqlite://" if request.param == "memory" else f"sqlite+pysqlite:///{(tmp_path / 'ingestion.db').as_posix()}"
    engine = create_engine(url)

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def counts(db):
    return tuple(db.scalar(select(func.count()).select_from(model)) for model in (Hackathon, Organization))


def test_raw_normalization():
    result = normalize_unstop_collection(envelope())
    assert result.rejected == 0 and len(result.events) == 1
    event = result.events[0]
    assert event.organization == "Builders" and event.source == "Unstop"
    assert event.description == "Build together" and event.location == "Online"
    assert event.start_date == datetime(2026, 10, 12, 4, 30)
    assert event.scraped_at == datetime(2026, 10, 12, 4, 30)


@pytest.mark.parametrize("changes", [
    {"http_status": 500}, {"status": "blocked"}, {"url": "https://unstop.com.evil.test/api/public/opportunity/search-result"},
    {"final_url": "https://unstop.com/api/private"}, {"url": "https://user@unstop.com/api/public/opportunity/search-result"},
    {"fetched_at": None}, {"fetched_at": "2026-10-12"}, {"fetched_at": "invalid"},
    {"raw_content": None}, {"raw_content": "not json"}, {"raw_content": "[]"},
    {"raw_content": '{"data": {"data": {}}}'}, {"raw_content": "x" * 5_000_001},
])
def test_invalid_envelopes_rejected(changes):
    with pytest.raises(ValueError):
        normalize_unstop_collection(envelope(**changes))


def test_missing_timestamp_and_oversized_item_list():
    raw = envelope()
    del raw["fetched_at"]
    with pytest.raises(ValueError):
        normalize_unstop_collection(raw)
    with pytest.raises(ValueError):
        normalize_unstop_collection(envelope([opportunity()] * 1001))


def test_invalid_items_counted_without_losing_valid_items():
    items = [opportunity(), None, [], opportunity(title=""), opportunity(organisation={}),
             opportunity(seo_url="https://unstop.com.evil.test/radar"),
             opportunity(end_date="2026-01-01"), opportunity(title="x" * 256)]
    result = normalize_unstop_collection(envelope(items))
    assert len(result.events) == 1 and result.rejected == 7


def test_insert_and_caller_commit(engine):
    with Session(engine) as db:
        result = ingest_events(db, normalize_unstop_collection(envelope()).events)
        assert (result.inserted, result.duplicates, result.organizations_created) == (1, 0, 1)
        db.commit()
    with Session(engine) as db:
        assert counts(db) == (1, 1)
        row = db.scalar(select(Hackathon))
        assert row.organization.name == "Builders" and row.start_date == datetime(2026, 10, 12, 4, 30)


def test_duplicates_in_batch_and_database_do_not_overwrite(engine):
    with Session(engine) as db:
        result = ingest_events(db, [record(), record(title="Replacement")])
        assert (result.inserted, result.duplicates, result.organizations_created) == (1, 1, 1)
        db.commit()
        result = ingest_events(db, [record(title="Another replacement"), record("https://unstop.com/hackathons/radar-2")])
        assert (result.inserted, result.duplicates, result.organizations_created) == (1, 1, 0)
        db.commit()
        assert counts(db) == (2, 1)
        assert db.scalar(select(Hackathon).order_by(Hackathon.id)).title == "Build a radar"


def test_caller_rollback_after_savepoint_release(engine):
    with Session(engine) as db:
        assert ingest_events(db, [record()]).inserted == 1
        assert counts(db) == (1, 1)
        db.rollback()
    with Session(engine) as db:
        assert counts(db) == (0, 0)


def test_session_close_does_not_commit(engine):
    with Session(engine) as db:
        ingest_events(db, [record()])
    with Session(engine) as db:
        assert counts(db) == (0, 0)


def test_failed_batch_rolls_back_all_batch_writes_preserves_caller_work(engine):
    with Session(engine) as db:
        db.add(Organization(name="Caller organization"))
        db.flush()

        def fail_second_event(_mapper, _connection, target):
            if target.title == "Fail second":
                # Real constraint violation inside the savepoint after earlier writes.
                target.organization_id = -999

        event.listen(Hackathon, "before_insert", fail_second_event)
        try:
            with pytest.raises(AppException) as info:
                ingest_events(db, [record(), record("https://unstop.com/hackathons/radar-2", title="Fail second")])
        finally:
            event.remove(Hackathon, "before_insert", fail_second_event)
        assert info.value.code == "DATABASE_ERROR" and info.value.status_code == 503
        assert counts(db) == (0, 1)
        assert db.scalar(select(Organization.name)) == "Caller organization"
        # Session remains usable and the caller can commit its existing work.
        db.commit()
    with Session(engine) as db:
        assert counts(db) == (0, 1)


def test_validation_occurs_before_writes(engine):
    with Session(engine) as db:
        with pytest.raises(ValueError):
            ingest_events(db, [record(), record(organization_id=123)])
        assert counts(db) == (0, 0)


def test_pending_caller_changes_are_not_implicitly_flushed(engine):
    with Session(engine) as db:
        db.add(Organization(name="Pending"))
        with pytest.raises(ValueError, match="clean session"):
            ingest_events(db, [record()])
        assert len(db.new) == 1
        db.rollback()


def test_retired_standalone_scraper_refuses_offline():
    from scraper.unstop import scrape
    with pytest.raises(RuntimeError, match="retired"):
        scrape()


@pytest.mark.parametrize("changes", [
    {"source": "Other"}, {"organization": " "}, {"organization_id": 1},
    {"url": "https://unstop.com:443/hackathons/radar"}, {"url": "https://unstop.com/\nradar"},
    {"url": "http://unstop.com/hackathons/radar"}, {"title": ""},
])
def test_invalid_ingestion_inputs_rejected_without_writes(engine, changes):
    with Session(engine) as db:
        with pytest.raises(ValueError):
            ingest_events(db, [record(**changes)])
        assert counts(db) == (0, 0)


def test_invalid_batch_type_and_size(engine):
    with Session(engine) as db:
        for records in (None, {}, [record()] * 1001, [None]):
            with pytest.raises(ValueError):
                ingest_events(db, records)
        assert counts(db) == (0, 0)
