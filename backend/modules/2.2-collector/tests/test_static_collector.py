import pytest

from collector_engine.collectors.static_collector import StaticCollector
from collector_engine.models import BlockedError, PermanentFetchError, Source, TemporaryFetchError


def test_static_collection_success(server, settings):
    resp = StaticCollector(settings).fetch(Source("s", f"{server}/ok", "static"))
    assert resp.http_status == 200
    assert "Hello static" in resp.content
    assert "text/html" in resp.content_type


def test_static_sends_our_user_agent(server, settings):
    resp = StaticCollector(settings).fetch(Source("s", f"{server}/ua", "static"))
    assert resp.content == settings.user_agent


def test_static_collects_json(server, settings):
    resp = StaticCollector(settings).fetch(Source("s", f"{server}/data.json", "static"))
    assert "json" in resp.content_type and '"items"' in resp.content


def test_static_server_error_is_temporary(server, settings):
    with pytest.raises(TemporaryFetchError):
        StaticCollector(settings).fetch(Source("s", f"{server}/error500", "static"))


def test_static_connection_failure_is_temporary(settings):
    with pytest.raises(TemporaryFetchError):
        StaticCollector(settings).fetch(Source("s", "http://127.0.0.1:1/", "static"))


def test_static_404_is_permanent(server, settings):
    with pytest.raises(PermanentFetchError):
        StaticCollector(settings).fetch(Source("s", f"{server}/notfound", "static"))


def test_static_403_is_blocked_not_retryable(server, settings):
    with pytest.raises(BlockedError):
        StaticCollector(settings).fetch(Source("s", f"{server}/forbidden", "static"))


def test_static_captcha_page_is_blocked(server, settings):
    with pytest.raises(BlockedError):
        StaticCollector(settings).fetch(Source("s", f"{server}/captcha", "static"))
