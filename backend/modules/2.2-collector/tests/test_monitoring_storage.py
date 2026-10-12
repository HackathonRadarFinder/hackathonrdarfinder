"""Item counts, block alerts, request headers, S3 storage."""
import io
import json

import pytest

from collector_engine.collectors.dynamic_collector import DynamicCollector
from collector_engine.collectors.static_collector import StaticCollector
from collector_engine.compliance.rate_limiter import RateLimiter
from collector_engine.config.loader import Settings
from collector_engine.items import count_items
from collector_engine.manager import CollectorManager
from collector_engine.models import Source
from collector_engine.monitoring.alerts import Alerter
from collector_engine.storage.factory import create_storage
from collector_engine.storage.local_storage import LocalRawStorage
from collector_engine.storage.s3_storage import S3RawStorage


@pytest.fixture
def manager(settings, transport):
    return CollectorManager(
        settings, LocalRawStorage(settings.raw_data_dir), rate_limiter=RateLimiter(0, 0), sleep=lambda s: None, transport=transport
    )


# ---------- item count ----------
def test_count_items_with_css_selector():
    assert count_items("<ul><li class='x'>1</li><li class='x'>2</li><li>3</li></ul>", "text/html", ".x") == 2


def test_count_items_json_list_and_unknown():
    assert count_items("[1,2,3]", "application/json") == 3
    assert count_items("<html></html>", "text/html") is None
    assert count_items("<html></html>", "text/html", "[[bad(") is None  # bad selector never breaks


def test_item_count_is_logged_stored_and_handed_off(manager, server, settings):
    src = Source("items", f"{server}/ok", "static", tos_allows_scraping=True, options={"item_selector": ".q"})
    result = manager.collect(src)
    assert result.item_count == 1
    record = LocalRawStorage(settings.raw_data_dir).load(result.storage_location)
    assert record["item_count"] == 1


def test_json_list_source_counts_items(manager, server):
    assert manager.collect(Source("j", f"{server}/list.json", "static", tos_allows_scraping=True)).item_count == 4


# ---------- alert on block ----------
def test_blocked_source_raises_alert_file_entry(manager, server, settings):
    result = manager.collect(Source("blk", f"{server}/forbidden", "static", tos_allows_scraping=True))
    assert result.status == "blocked"
    lines = (settings.log_dir / "alerts.log").read_text().splitlines()
    event = json.loads(lines[-1])
    assert event["type"] == "blocked" and event["source_id"] == "blk"


def test_alert_calls_webhook_and_survives_webhook_failure(tmp_path):
    import requests

    from collector_engine.models import CollectionResult

    calls = []

    class Session:
        def post(self, url, json=None, timeout=None):
            calls.append((url, json))

    r = CollectionResult("s", "http://x", "static", status="blocked", error="HTTP 403")
    Alerter(tmp_path, "http://hook.test", Session()).blocked(r)
    assert calls and "blocked" in calls[0][1]["text"]

    class Broken:
        def post(self, *a, **k):
            raise requests.ConnectionError("down")

    Alerter(tmp_path, "http://hook.test", Broken()).blocked(r)  # must not raise


def test_non_blocked_results_do_not_alert(manager, server, settings):
    manager.collect(Source("fine", f"{server}/ok", "static", tos_allows_scraping=True))
    manager.collect(Source("nf", f"{server}/notfound", "static", tos_allows_scraping=True))
    assert not (settings.log_dir / "alerts.log").exists()


# ---------- headers ----------
def test_static_collector_sends_identifying_headers(server, settings, transport):
    settings.contact_email = "bot-owner@example.com"
    resp = StaticCollector(settings, transport=transport).fetch(Source("h", f"{server}/headers", "static", tos_allows_scraping=True))
    sent = json.loads(resp.content)
    assert sent["User-Agent"] == settings.user_agent
    assert sent["From"] == "bot-owner@example.com"
    assert "text/html" in sent["Accept"]


def test_dynamic_collector_refuses_headers_request(server, settings, hits):
    from collector_engine.models import BlockedError
    with pytest.raises(BlockedError, match="disabled"):
        DynamicCollector(settings).fetch(Source("h", f"{server}/headers", "dynamic", tos_allows_scraping=True))
    assert hits == {}


# ---------- S3 storage (in-memory fake client, no AWS needed) ----------
class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, ContentType=None):
        self.objects[(Bucket, Key)] = Body

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}

    def head_object(self, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise KeyError(Key)

    def get_paginator(self, name):
        outer = self

        class P:
            def paginate(self, Bucket, Prefix):
                yield {"Contents": [{"Key": k} for (b, k) in outer.objects if b == Bucket and k.startswith(Prefix)]}

        return P()


def test_s3_storage_round_trip_through_manager(settings, server, transport):
    fake = FakeS3()
    storage = S3RawStorage("my-bucket", "raw", client=fake)
    manager = CollectorManager(settings, storage, rate_limiter=RateLimiter(0, 0), sleep=lambda s: None, transport=transport)
    result = manager.collect(Source("s3src", f"{server}/ok", "static", tos_allows_scraping=True, options={"item_selector": ".q"}))

    assert result.status == "success"
    keys = sorted(k for (_, k) in fake.objects)
    assert keys[0].startswith("raw/s3src/") and keys[0].endswith(".html")
    assert keys[1].endswith(".meta.json")
    record = storage.load(result.storage_location)
    assert {"source_id", "fetched_at", "url", "http_status", "raw_content"} <= record.keys()
    assert "Hello static" in record["raw_content"] and record["item_count"] == 1
    assert storage.list_locations("s3src") == [result.storage_location]


def test_s3_same_second_does_not_overwrite():
    from collector_engine.models import CollectionResult

    fake = FakeS3()
    storage = S3RawStorage("b", "raw/", client=fake)
    r = lambda: CollectionResult("s", "http://x", "static", status="success", fetched_at="2026-10-07T10:30:00Z",
                                 http_status=200, raw_content="<p>x</p>", content_type="text/html")
    a, b = storage.save(r()), storage.save(r())
    assert a != b and len(storage.list_locations("s")) == 2


def test_storage_factory_selects_backend(tmp_path):
    assert isinstance(create_storage(Settings(raw_data_dir=tmp_path)), LocalRawStorage)
    with pytest.raises(ValueError):
        create_storage(Settings(storage_backend="s3", s3_bucket=""))  # bucket required
    with pytest.raises(ValueError):
        create_storage(Settings(storage_backend="ftp"))
