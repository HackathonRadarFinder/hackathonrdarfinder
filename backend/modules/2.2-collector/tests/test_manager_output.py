"""Integration tests: the full pipeline through CollectorManager + handoff output."""
import json

import pytest

from collector_engine.compliance.rate_limiter import RateLimiter
from collector_engine.manager import CollectorManager
from collector_engine.models import Source
from collector_engine.storage.local_storage import LocalRawStorage

REQUIRED = {"source_id", "fetched_at", "url", "http_status", "raw_content"}


@pytest.fixture
def manager(settings):
    return CollectorManager(
        settings,
        LocalRawStorage(settings.raw_data_dir),
        rate_limiter=RateLimiter(0, 0),
        sleep=lambda s: None,
    )


def test_success_produces_handoff_record_with_required_fields(manager, server, settings):
    result = manager.collect(Source("ok_src", f"{server}/ok", "static"))
    assert result.status == "success" and result.attempts == 1

    record = LocalRawStorage(settings.raw_data_dir).load(result.storage_location)
    assert REQUIRED <= record.keys()
    assert record["source_id"] == "ok_src"
    assert record["url"] == f"{server}/ok"
    assert record["http_status"] == 200
    assert "Hello static" in record["raw_content"]
    assert record["fetched_at"].endswith("Z") and "T" in record["fetched_at"]
    json.dumps(record)  # must be JSON-serialisable


def test_raw_html_and_metadata_files_are_written(manager, server, settings):
    result = manager.collect(Source("files_src", f"{server}/ok", "static"))
    folder = settings.raw_data_dir / "files_src"
    assert len(list(folder.glob("*.html"))) == 1
    meta = json.loads((settings.raw_data_dir / result.storage_location).read_text())
    assert "raw_content" not in meta and meta["raw_file"].endswith(".html")
    assert meta["status"] == "success"


def test_json_source_is_stored_as_json_file(manager, server, settings):
    manager.collect(Source("json_src", f"{server}/data.json", "static"))
    assert len(list((settings.raw_data_dir / "json_src").glob("*.json"))) == 2  # raw + meta


def test_robots_disallowed_is_skipped_and_never_fetched(manager, server, hits):
    result = manager.collect(Source("blocked_by_robots", f"{server}/private/secret", "static"))
    assert result.status == "skipped"
    assert result.robots_allowed is False
    assert "/private/secret" not in hits  # the page itself was never requested
    assert result.attempts == 0


def test_robots_disallowed_applies_to_dynamic_collector_too(manager, server, hits):
    result = manager.collect(Source("d", f"{server}/private/secret", "dynamic"))
    assert result.status == "skipped"
    assert "/private/secret" not in hits


def test_tos_prohibited_source_is_skipped(manager, server, hits):
    src = Source("tos", f"{server}/ok", "static", tos_allows_scraping=False, tos_note="ToS section 4")
    result = manager.collect(src)
    assert result.status == "skipped" and "ToS" in result.robots_reason
    assert hits == {}  # no request at all, not even robots.txt


def test_temporary_failure_is_retried_then_succeeds(manager, server):
    result = manager.collect(Source("flaky", f"{server}/flaky", "static"))
    assert result.status == "success" and result.attempts == 3


def test_persistent_failure_stops_after_3_attempts(manager, server, hits):
    result = manager.collect(Source("down", f"{server}/error500", "static"))
    assert result.status == "failed"
    assert result.attempts == 3
    assert hits["/error500"] == 3


def test_403_is_recorded_as_blocked_without_retry(manager, server, hits):
    result = manager.collect(Source("forbidden", f"{server}/forbidden", "static"))
    assert result.status == "blocked"
    assert hits["/forbidden"] == 1


def test_404_fails_without_retry(manager, server, hits):
    result = manager.collect(Source("nf", f"{server}/notfound", "static"))
    assert result.status == "failed" and hits["/notfound"] == 1


def test_unknown_collector_type_fails_before_any_request(manager, server, hits):
    result = manager.collect(Source("x", f"{server}/ok", "carrier-pigeon"))
    assert result.status == "failed" and hits == {}


def test_dynamic_source_runs_through_playwright(manager, server, settings):
    src = Source("dyn", f"{server}/js", "dynamic", options={"wait_for_selector": ".q"})
    result = manager.collect(src)
    assert result.status == "success"
    assert "rendered by javascript" in result.raw_content


def test_run_processes_all_sources_and_reports_each(manager, server):
    results = manager.run([
        Source("a", f"{server}/ok", "static"),
        Source("b", f"{server}/private/x", "static"),
    ])
    assert [r.status for r in results] == ["success", "skipped"]
