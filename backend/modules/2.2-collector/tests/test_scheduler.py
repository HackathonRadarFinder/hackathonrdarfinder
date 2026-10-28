"""Scheduler fixtures never use the application's database or external network."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from unittest.mock import Mock

import pytest

from collector_engine.manager import CollectorManager
from collector_engine.models import Source
from collector_engine.scheduler import (ScheduleState, ScheduledJob, load_schedule,
                                        main, run_due)
from collector_engine.config.loader import ConfigError
from collector_engine.storage.local_storage import LocalRawStorage


NOW = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)


def job(**changes):
    values = dict(source_id="fixture", interval_seconds=3600, enabled=True,
                  adapter_version="fixture-v1", approval={
                      "owner": "Fixture owner", "basis": "Local test server owned by tests",
                      "reference": "Fixture test_scheduler.py", "reviewed_at": "2026-10-01T00:00:00Z",
                      "expires_at": "2026-11-01T00:00:00Z"})
    return ScheduledJob(**{**values, **changes})


def source(server, **changes):
    return Source(**{**dict(source_id="fixture", url=f"{server}/ok", type="static",
                    tos_allows_scraping=True, tos_note="Local fixture explicitly owned by tests"), **changes})


@pytest.fixture
def state(tmp_path):
    instance = ScheduleState(tmp_path / "schedule.sqlite3")
    yield instance
    instance.close()


@pytest.fixture
def manager(settings, transport):
    return CollectorManager(settings, LocalRawStorage(settings.raw_data_dir),
                            transport=transport, sleep=lambda delay: None)


@pytest.mark.parametrize("enabled, run", [(False, False), (False, True), (True, False)])
def test_cli_requires_both_opt_ins_without_state_or_requests(tmp_path, enabled, run, capsys):
    config = tmp_path / "schedule.json"
    config.write_text(json.dumps({"enabled": enabled, "jobs": []}))
    db = tmp_path / "not-created" / "state.sqlite3"
    args = ["--config", str(config), "--state", str(db), "--sources", "missing-sources.json"]
    assert main(args + (["--run"] if run else [])) == 0
    assert not db.exists() and not db.parent.exists()
    assert json.loads(capsys.readouterr().out)["executed"] is False


@pytest.mark.parametrize("patch", [dict(enabled="true"), dict(jobs=[{"source_id": "../unsafe", "interval_seconds": 3600}]),
    dict(jobs=[{"source_id": "fixture", "interval_seconds": 1}]),
    dict(jobs=[{"source_id": "fixture", "interval_seconds": 3600, "enabled": 1}])])
def test_schedule_rejects_unsafe_or_coerced_configuration(tmp_path, patch):
    config = tmp_path / "schedule.json"
    config.write_text(json.dumps({"enabled": False, "jobs": [], **patch}))
    with pytest.raises(ConfigError):
        load_schedule(config)


def test_duplicate_jobs_rejected_before_execution(tmp_path):
    config = tmp_path / "schedule.json"
    item = {"source_id": "fixture", "interval_seconds": 3600}
    config.write_text(json.dumps({"enabled": True, "jobs": [item, item]}))
    with pytest.raises(ConfigError):
        load_schedule(config)


@pytest.mark.parametrize("source_patch, job_patch, reason", [
    ({"enabled": False}, {}, "source_disabled"),
    ({"tos_allows_scraping": False}, {}, "permission_missing"),
    ({"tos_note": ""}, {}, "permission_missing"),
    ({}, {"approval": {}}, "approval_missing"),
    ({}, {"adapter_version": ""}, "adapter_unreviewed"),
    ({}, {"approval": {**job().approval, "expires_at": "2026-10-10T00:00:00Z"}}, "approval_expired"),
    ({}, {"approval": {**job().approval, "reviewed_at": "2026-10-20T00:00:00Z"}}, "approval_invalid"),
    ({}, {"approval": {**job().approval, "reviewed_at": "2026-10-01T00:00:00"}}, "approval_invalid"),
])
def test_unapproved_stale_and_disabled_sources_record_skip_without_network(state, server, hits,
                                                                          source_patch, job_patch, reason):
    manager = Mock()
    result = run_due([job(**job_patch)], [source(server, **source_patch)], state, manager, clock=lambda: NOW)
    assert result["skipped"] == 1 and not hits
    manager.collect.assert_not_called()
    row = state.db.execute("SELECT * FROM collection_runs").fetchone()
    assert row["status"] == "skipped" and row["policy_decision"] == reason and row["ended_at"]


def test_due_run_persists_success_checksum_and_interval_without_overwriting(state, server, manager, hits):
    first = run_due([job()], [source(server)], state, manager, clock=lambda: NOW)
    assert first["success"] == 1 and hits["/ok"] == 1
    row = state.db.execute("SELECT * FROM collection_runs").fetchone()
    record = manager.storage.load(row["storage_location"])
    assert row["checksum"] == hashlib.sha256(record["raw_content"].encode()).hexdigest()
    assert row["http_status"] == 200 and row["policy_decision"] == "robots_allowed"
    assert row["adapter_version"] == "fixture-v1" and row["latency_ms"] >= 0
    assert run_due([job()], [source(server)], state, manager, clock=lambda: NOW)["not_due"] == 1
    assert hits["/ok"] == 1
    assert run_due([job()], [source(server)], state, manager,
                   clock=lambda: NOW + timedelta(hours=1))["success"] == 1
    assert state.db.execute("SELECT COUNT(*) FROM collection_runs").fetchone()[0] == 2


@pytest.mark.parametrize("path, status, requests", [("/private/secret", "skipped", 0),
                                                   ("/forbidden", "blocked", 1), ("/error500", "failed", 3)])
def test_existing_policy_blocks_and_failures_remain_durable(state, server, manager, hits, path, status, requests):
    result = run_due([job()], [source(server, url=server + path)], state, manager, clock=lambda: NOW)
    assert result[status] == 1 and hits.get(path, 0) == requests
    row = state.db.execute("SELECT * FROM collection_runs").fetchone()
    assert row["status"] == status and row["checksum"] is None and row["ended_at"]


def test_overlapping_and_crashed_scheduler_claims_cannot_run(state, server, tmp_path, hits):
    assert state.acquire("crashed-owner")
    second = ScheduleState(tmp_path / "schedule.sqlite3")
    try:
        manager = Mock()
        assert run_due([job()], [source(server)], second, manager, clock=lambda: NOW)["not_due"] == 1
        second.release("different-owner")
        assert not second.acquire("different-owner")
        manager.collect.assert_not_called()
        assert not hits
    finally:
        second.close()
        state.release("crashed-owner")


def test_crashed_source_claim_does_not_retry_or_steal(state, server):
    state.claim(job(), NOW, None)
    manager = Mock()
    assert run_due([job()], [source(server)], state, manager,
                   clock=lambda: NOW + timedelta(days=1))["not_due"] == 1
    manager.collect.assert_not_called()
    assert state.db.execute("SELECT status FROM collection_runs").fetchone()[0] == "running"


def test_unexpected_exception_is_failed_without_persisting_secrets(state, server):
    manager = Mock()
    manager.collect.side_effect = RuntimeError("secret-exception-test-marker")
    assert run_due([job()], [source(server)], state, manager, clock=lambda: NOW)["failed"] == 1
    row = state.db.execute("SELECT * FROM collection_runs").fetchone()
    assert row["reason"] == "collector_exception" and "secret-exception-test-marker" not in str(dict(row))
    assert state.db.execute("SELECT COUNT(*) FROM scheduler_lock").fetchone()[0] == 0


def test_disabled_job_never_creates_run_or_requests(state, server):
    manager = Mock()
    assert run_due([job(enabled=False)], [source(server)], state, manager, clock=lambda: NOW)["success"] == 0
    assert state.db.execute("SELECT COUNT(*) FROM collection_runs").fetchone()[0] == 0
    manager.collect.assert_not_called()


def test_enabled_cli_unapproved_source_never_initializes_storage_clients(tmp_path, monkeypatch, capsys):
    config = tmp_path / "schedule.json"
    config.write_text(json.dumps({"enabled": True, "jobs": [{"source_id": "fixture",
                           "interval_seconds": 3600, "enabled": True}]}))
    sources = tmp_path / "sources.json"
    sources.write_text(json.dumps({"sources": [{"source_id": "fixture", "url": "https://example.org/",
                                                 "type": "static", "tos_allows_scraping": False}]}))
    def forbidden(*args):
        raise AssertionError("Unapproved source must not initialize storage or logging")
    monkeypatch.setattr("collector_engine.scheduler.create_storage", forbidden)
    monkeypatch.setattr("collector_engine.scheduler.setup_logging", forbidden)
    monkeypatch.setenv("COLLECTOR_STORAGE", "s3")
    assert main(["--config", str(config), "--sources", str(sources), "--state", str(tmp_path / "state.sqlite3"), "--run"]) == 0
    assert json.loads(capsys.readouterr().out)["skipped"] == 1
