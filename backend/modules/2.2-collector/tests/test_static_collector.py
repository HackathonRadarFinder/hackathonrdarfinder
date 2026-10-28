import json

import pytest

from collector_engine.collectors.static_collector import StaticCollector
from collector_engine.compliance.robots_checker import RobotsChecker
from collector_engine.models import BlockedError, PermanentFetchError, Source, TemporaryFetchError


@pytest.fixture
def collector(settings, transport):
    robots = RobotsChecker(settings.user_agent, transport=transport)
    return StaticCollector(settings, transport=transport, authorize=robots.authorize)


def source(server, path):
    return Source("s", f"{server}{path}", "static", tos_allows_scraping=True)


def test_static_collection_success(server, collector):
    resp = collector.fetch(source(server, "/ok"))
    assert resp.http_status == 200 and "Hello static" in resp.content
    assert "text/html" in resp.content_type


def test_static_sends_identifying_headers(server, collector, settings):
    settings.contact_email = "bot-owner@example.com"
    sent = json.loads(collector.fetch(source(server, "/headers")).content)
    assert sent["User-Agent"] == settings.user_agent
    assert sent["From"] == settings.contact_email
    assert "text/html" in sent["Accept"]


def test_static_collects_json(server, collector):
    resp = collector.fetch(source(server, "/data.json"))
    assert "json" in resp.content_type and '"items"' in resp.content


@pytest.mark.parametrize("path,error", [("/error500", TemporaryFetchError),
                                        ("/notfound", PermanentFetchError),
                                        ("/forbidden", BlockedError),
                                        ("/throttled", BlockedError),
                                        ("/captcha", BlockedError)])
def test_static_classifies_failures(server, collector, path, error):
    with pytest.raises(error):
        collector.fetch(source(server, path))


def test_static_allowed_redirect_preserves_final_url(server, collector, hits):
    resp = collector.fetch(source(server, "/redirect-ok"))
    assert resp.final_url == f"{server}/ok" and "Hello static" in resp.content
    assert hits["/redirect-ok"] == hits["/ok"] == 1
