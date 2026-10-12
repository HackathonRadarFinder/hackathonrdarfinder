"""Offline regressions for authorization and bounded transport."""
import socket

import pytest

from collector_engine.collectors.static_collector import StaticCollector
from collector_engine.compliance.robots_checker import RobotsChecker
from collector_engine.manager import CollectorManager
from collector_engine.models import ComplianceError, PermanentFetchError, Source
from collector_engine.network import HttpTransport, URLPolicy
from collector_engine.storage.local_storage import LocalRawStorage


def test_same_origin_redirect_denied_before_content(settings, transport, server, hits):
    robots = RobotsChecker(settings.user_agent, transport=transport)
    collector = StaticCollector(settings, transport=transport, authorize=robots.authorize)
    with pytest.raises(ComplianceError, match="disallowed"):
        collector.fetch(Source("s", f"{server}/redirect-private", "static", tos_allows_scraping=True))
    assert hits == {"/robots.txt": 1, "/redirect-private": 1}


def test_manager_records_redirect_refusal(settings, transport, server, hits):
    manager = CollectorManager(settings, LocalRawStorage(settings.raw_data_dir), transport=transport)
    result = manager.collect(Source("s", f"{server}/redirect-private", "static", tos_allows_scraping=True))
    assert result.status == "skipped" and result.robots_allowed is False
    assert result.attempts == 1 and result.storage_location is None
    assert "/private/secret" not in hits


def test_cross_origin_redirect_refused_before_dns(transport, server, server_config, monkeypatch, hits):
    server_config["outside_url"] = "http://forbidden.test/path"
    original = transport.policy.resolver
    resolved = []

    def resolve(host, *args, **kwargs):
        resolved.append(host)
        return original(host, *args, **kwargs)

    transport.policy.resolver = resolve
    with pytest.raises(PermanentFetchError, match="origin"):
        transport.request(f"{server}/redirect-outside")
    assert resolved == ["127.0.0.1"] and hits == {"/redirect-outside": 1}


@pytest.mark.parametrize("address", ["127.0.0.1", "10.1.2.3", "169.254.169.254", "0.0.0.0", "192.0.2.1"])
def test_nonpublic_addresses_refused(address):
    def resolver(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 80))]
    policy = URLPolicy(["http://fixture.test"], resolver=resolver)
    with pytest.raises(PermanentFetchError, match="forbidden"):
        policy.resolve("http://fixture.test/page")


def test_mixed_public_private_dns_answers_refused():
    answers = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 80))
               for address in ("8.8.8.8", "10.0.0.1")]
    policy = URLPolicy(["http://fixture.test"], resolver=lambda *a, **k: answers)
    with pytest.raises(PermanentFetchError):
        policy.resolve("http://fixture.test")


@pytest.mark.parametrize("path", ["oversized", "oversized-no-length"])
def test_byte_limit(transport, server, path):
    transport.max_bytes = 128
    with pytest.raises(PermanentFetchError, match="byte limit"):
        transport.request(f"{server}/{path}")


def test_redirect_limit(transport, server, hits):
    transport.max_redirects = 2
    with pytest.raises(PermanentFetchError, match="redirect limit"):
        transport.request(f"{server}/redirect-loop")
    assert hits["/redirect-loop"] == 3


def test_authorization_precedes_rate_limit_and_request(transport, server, hits):
    calls = []
    transport.before_request = lambda url: calls.append(("rate", url))
    transport.request(f"{server}/redirect-ok", authorize=lambda url: calls.append(("authorize", url)))
    assert calls == [(kind, f"{server}/{path}") for path in ("redirect-ok", "ok")
                     for kind in ("authorize", "rate")]


@pytest.mark.parametrize("status", [401, 403, 429, 500, 302])
def test_unverifiable_robots_never_allows_content(transport, server, server_config, hits, status):
    server_config["robots_status"] = status
    robots = RobotsChecker("TestCollector", transport=transport)
    with pytest.raises(ComplianceError):
        robots.authorize(f"{server}/ok")
    assert "/ok" not in hits


def test_robots_redirect_cannot_fetch_unapproved_content(transport, server, server_config, hits):
    server_config.update(robots_status=302, robots_location="/private/secret")
    robots = RobotsChecker("TestCollector", transport=transport)
    with pytest.raises(ComplianceError):
        robots.authorize(f"{server}/ok")
    assert hits == {"/robots.txt": 1}


@pytest.mark.parametrize("permission", [False, None])
def test_permission_required_before_any_request(settings, transport, server, hits, permission):
    kwargs = {} if permission is None else {"tos_allows_scraping": permission}
    src = Source("s", f"{server}/ok", "static", **kwargs)
    with pytest.raises(ComplianceError, match="permission"):
        StaticCollector(settings, transport=transport).fetch(src)
    manager = CollectorManager(settings, LocalRawStorage(settings.raw_data_dir), transport=transport)
    assert manager.collect(src).status == "skipped"
    assert hits == {}


def test_job_deadline_shared_and_reset(transport, server, hits, monkeypatch):
    import collector_engine.network as network
    now = [0.0]
    monkeypatch.setattr(network.time, "monotonic", lambda: now[0])
    transport.max_job_seconds = 10
    with transport.budget():
        transport.request(f"{server}/ok")
        now[0] = 11
        with pytest.raises(PermanentFetchError, match="time budget"):
            transport.request(f"{server}/ok")
    assert hits == {"/ok": 1} and transport.deadline is None
    transport.request(f"{server}/ok")
    assert hits["/ok"] == 2


def test_manager_retry_cannot_reset_deadline(settings, transport, server, hits, monkeypatch):
    import collector_engine.network as network
    now = [0.0]
    monkeypatch.setattr(network.time, "monotonic", lambda: now[0])
    transport.max_job_seconds = 1
    settings.backoff_base = 2
    slept = []

    def sleep(seconds):
        slept.append(seconds)
        now[0] += seconds

    manager = CollectorManager(settings, LocalRawStorage(settings.raw_data_dir),
                               transport=transport, sleep=sleep)
    result = manager.collect(Source("s", f"{server}/error500", "static", tos_allows_scraping=True))
    assert result.status == "failed" and "time budget" in result.error
    assert hits["/error500"] == 1 and slept == [1]
    assert transport.deadline is None


def test_connection_uses_validated_numeric_address(monkeypatch):
    import collector_engine.network as network
    calls = []
    address = (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 80))

    class FakeSocket:
        def settimeout(self, value):
            calls.append(("timeout", value))

        def connect(self, value):
            calls.append(("connect", value))

    monkeypatch.setattr(network.socket, "socket", lambda *args: FakeSocket())
    network._PinnedHTTPConnection("fixture.test", 80, address, 2).connect()
    assert calls == [("timeout", 2), ("connect", ("8.8.8.8", 80))]


def test_https_context_verifies_certificates_and_hostname():
    import ssl
    from collector_engine.network import _PinnedHTTPSConnection
    connection = _PinnedHTTPSConnection("fixture.test", 443, None, 2)
    assert connection._context.verify_mode == ssl.CERT_REQUIRED
    assert connection._context.check_hostname is True


def test_zero_port_rejected():
    from collector_engine.network import parsed_url
    with pytest.raises(PermanentFetchError):
        parsed_url("http://fixture.test:0/page")
