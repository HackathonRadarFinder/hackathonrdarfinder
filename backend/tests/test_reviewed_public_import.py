"""Offline public-page export/import contract; disposable databases only."""
import csv
import hashlib
import json
from pathlib import Path
import socket

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.core import EventVersion
from app.models.hackathon import Hackathon
from radar_collector.radar_scraper import collect, save
from workers.import_reviewed_public import load_approved, stage


@pytest.fixture
def candidates(tmp_path, monkeypatch):
    original_connect = socket.socket.connect

    def forbidden(sock, address):
        # Windows asyncio uses a loopback socketpair for its internal wakeup.
        if isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1"}:
            return original_connect(sock, address)
        raise AssertionError("offline verification must not contact external hosts")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    base = Path(__file__).resolve().parents[1] / "radar_collector"
    result = collect({}, base / "seed_urls.txt", tmp_path, discover=True,
                     max_pages=20, delay=1, offline=base / "fixtures")
    assert result["candidate_records"] == 4
    assert result["errors_or_denials"] == 0
    rows = json.loads((tmp_path / "candidates.json").read_text(encoding="utf-8"))
    with (tmp_path / "candidates.csv").open(encoding="utf-8-sig", newline="") as f:
        assert list(csv.DictReader(f)) == rows
    for row in rows:
        fixture = base / "fixtures" / (hashlib.sha256(row["url"].encode()).hexdigest()[:16] + ".html")
        assert row["source_hash"] == hashlib.sha256(fixture.read_bytes()).hexdigest()
    return tmp_path, rows


def test_unreviewed_export_is_skipped(candidates):
    path, rows = candidates
    assert load_approved(path / "candidates.csv") == ([], 4)
    assert [r["title"] for r in rows] == ["Hacknauts 2.0", "DevNexus 2.0", "AI Product Hackathon", "Data Analytics Hackathon"]
    assert [r["organization"] for r in rows] == ["Causmic Club", "", "Product Space", "Gradient Learnings"]
    assert [r["prize"] for r in rows] == ["", "", "\u20b9 90,000", "\u20b9 59,500"]
    assert [r["location"] for r in rows] == ["Ludhiana, India", "Kolkata, India", "", ""]
    assert [r["source"] for r in rows] == ["Devfolio", "Devfolio", "Unstop", "Unstop"]
    assert [(r["start_date"], r["end_date"]) for r in rows] == [
        ("2026-11-14T00:00:00", "2026-11-15T00:00:00"),
        ("2026-11-28T00:00:00", "2026-11-29T00:00:00"), ("", ""), ("", "")]
    assert all(r["registration_deadline"] == "" for r in rows)


def test_missing_organizer_cannot_be_approved(candidates):
    path, rows = candidates
    rows[1]["review_status"] = "approved"
    save(rows, path)
    with pytest.raises(ValidationError):
        load_approved(path / "candidates.csv")


def test_reviewed_schema_duplicates_provenance_and_rollback(candidates):
    path, rows = candidates
    # Simulate review only inside temporary test files, never production exports.
    for i in (0, 2, 3):
        rows[i]["review_status"] = "approved"
        rows[i]["collection_mode"] = "reviewed_manual"
        rows[i]["permission_reference"] = "synthetic test authorization; not a real source approval"
    save(rows, path)
    approved, skipped = load_approved(path / "candidates.csv")
    assert len(approved) == 3 and skipped == 1
    engine = create_engine("sqlite+pysqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        assert stage(db, approved + approved[:1], "offline-test") == {"inserted": 3, "duplicate_urls": 1}
        assert stage(db, approved, "offline-test") == {"inserted": 0, "duplicate_urls": 3}
        versions = db.scalars(select(EventVersion)).all()
        assert len(versions) == 3
        assert {v.changes["source_html_sha256"] for v in versions} == {r.source_hash for r in approved}
        assert all(v.changes["manual_reviewer"] == "offline-test" for v in versions)
        db.rollback()
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Hackathon)) == 0
    engine.dispose()


def synthetic_approved(candidates):
    path, rows = candidates
    for i in (0, 2, 3):
        rows[i].update(review_status="approved", collection_mode="reviewed_manual",
                       permission_reference="synthetic test authorization")
    save(rows, path)
    return load_approved(path / "candidates.csv")[0]


def test_fixture_export_cannot_be_approved(candidates):
    path, rows = candidates
    rows[0]["review_status"] = "approved"
    save(rows, path)
    with pytest.raises(ValueError, match="fixtures cannot be imported"):
        load_approved(path / "candidates.csv")


@pytest.mark.parametrize("change", [
    {"permission_reference": ""}, {"source_hash": "invalid"},
    {"date_precision": "invented"}, {"collection_mode": "offline_fixture"},
])
def test_stage_revalidates_before_writes(candidates, change):
    records = synthetic_approved(candidates)
    records[-1] = records[-1]._replace(**change)
    engine = create_engine("sqlite+pysqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        with pytest.raises(ValueError):
            stage(db, records, "test-reviewer")
        assert db.scalar(select(func.count()).select_from(Hackathon)) == 0
    engine.dispose()


def test_late_provenance_failure_rolls_back_batch(candidates):
    from sqlalchemy import event
    from app.models.organization import Organization
    records = synthetic_approved(candidates)
    engine = create_engine("sqlite+pysqlite://")
    Base.metadata.create_all(engine)

    def fail(*args):
        raise ValueError("simulated provenance storage failure")

    with Session(engine) as db:
        db.add(Organization(name="Unrelated caller data"))
        db.flush()
        event.listen(EventVersion, "before_insert", fail)
        try:
            with pytest.raises(ValueError, match="provenance storage failure"):
                stage(db, records, "test-reviewer")
        finally:
            event.remove(EventVersion, "before_insert", fail)
        assert db.scalar(select(func.count()).select_from(Hackathon)) == 0
        assert db.scalar(select(func.count()).select_from(EventVersion)) == 0
        assert db.scalars(select(Organization.name)).all() == ["Unrelated caller data"]
        db.commit()
    engine.dispose()


def test_approved_records_commit_and_are_publicly_retrievable(candidates, tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db
    from sqlalchemy.orm import sessionmaker

    records = synthetic_approved(candidates)
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / 'api.db').as_posix()}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory.begin() as db:
        result = stage(db, records, "test-reviewer")
        assert result["inserted"] == 3
    with factory.begin() as db:
        # Tracking parameters and trailing slashes do not create new records.
        from app.schemas.event import EventCreate
        payload = records[1].event.model_dump()
        payload["url"] = str(records[1].event.url) + "/?utm_source=test"
        variant = records[1]._replace(event=EventCreate.model_validate(payload))
        assert stage(db, [variant], "test-reviewer")["duplicate_urls"] == 1

    def isolated_db():
        with factory() as db:
            yield db

    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = isolated_db
    try:
        with TestClient(app) as client:
            response = client.get("/events/")
            assert response.status_code == 200
            items = response.json()["data"]
            assert len(items) == 3
            assert {r["source"] for r in items} == {"Unstop", "Devfolio"}
            assert {r["url"] for r in items} == {str(r.event.url) for r in records}
            for item in items:
                detail = client.get(f"/events/{item['id']}")
                assert detail.status_code == 200
                assert detail.json()["data"] == item
            page = client.get("/events/", params={"page": 1, "page_size": 2})
            assert page.status_code == 200 and page.json()["total"] == 3
            assert len(page.json()["data"]) == 2
            # Unknown dates remain unknown through storage and API serialization.
            assert all(r["start_date"] is None for r in items if r["source"] == "Unstop")
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()


def test_generated_json_event_schema_contract(candidates):
    from app.schemas.event import EventCreate
    from workers.import_reviewed_public import ACCEPT
    _, rows = candidates
    for i, row in enumerate(rows):
        payload = {key: row.get(key) or None for key in ACCEPT}
        if i == 1:
            with pytest.raises(ValidationError):
                EventCreate.model_validate(payload)
        else:
            event = EventCreate.model_validate(payload)
            assert event.title == row["title"] and event.source == row["source"]


@pytest.mark.parametrize("url,source", [
    ("https://cdn.devfolio.co/", "Devfolio"),
    ("https://status.devfolio.co/", "Devfolio"),
    ("https://unstop.com.evil.test/o/123", "Unstop"),
    ("https://unstop.com/o/123\n", "Unstop"),
    ("https://user@unstop.com/o/123", "Unstop"),
])
def test_importer_source_boundaries(url, source):
    from workers.import_reviewed_public import approved_source
    assert not approved_source(url, source)



def test_future_devfolio_adapter_fails_closed():
    from datetime import datetime, timezone
    from app.services.discovery_service import curated_policy, policy_reason, collect_source
    from app.schemas.discovery import SourcePolicy
    now = datetime.now(timezone.utc)
    policy = curated_policy(now, enabled=True)
    payload = policy.model_dump()
    payload.update(adapter="devfolio-v1", url="https://example.devfolio.co/")
    with pytest.raises(ValidationError):
        SourcePolicy.model_validate(payload)
    # Defense in depth even if an internal caller constructs an unchecked model.
    future = policy.model_copy(update={"adapter": "devfolio-v1"})
    assert policy_reason(future, now, allow_live=True) == "unsupported_adapter"
    with pytest.raises(ValueError, match="unsupported_adapter"):
        collect_source(future)


def test_concurrent_sqlite_imports_skip_duplicates(candidates, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    records = synthetic_approved(candidates)
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / 'concurrent.db').as_posix()}",
                           connect_args={"check_same_thread": False, "timeout": 10})
    Base.metadata.create_all(engine)
    ready = Barrier(2)

    def import_batch():
        ready.wait(timeout=10)
        with Session(engine) as db, db.begin():
            return stage(db, records, "concurrent-test")

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: import_batch(), range(2)))
        assert sorted(r["inserted"] for r in results) == [0, 3]
        assert sorted(r["duplicate_urls"] for r in results) == [0, 3]
        with Session(engine) as db:
            assert db.scalar(select(func.count()).select_from(Hackathon)) == 3
            assert db.scalar(select(func.count()).select_from(EventVersion)) == 3
    finally:
        engine.dispose()
