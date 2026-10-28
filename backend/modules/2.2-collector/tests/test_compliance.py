import pytest

from collector_engine.compliance.rate_limiter import RateLimiter
from collector_engine.compliance.robots_checker import RobotsChecker
from collector_engine.compliance.tos_checker import TosChecker
from collector_engine.models import Source
from collector_engine.network import HTTPResponse

UA = "TestCollector/1.0 (+test)"


def test_robots_allowed_url(server, transport):
    result = RobotsChecker(UA, transport=transport).check(f"{server}/ok")
    assert result.allowed is True


def test_robots_disallowed_url(server, transport):
    result = RobotsChecker(UA, transport=transport).check(f"{server}/private/secret")
    assert result.allowed is False
    assert "disallowed" in result.reason


def test_robots_missing_file_means_allowed(server):
    # /ok is not a robots.txt host root issue: use a different origin that returns 404 for robots
    class FakeTransport:
        def request(self, *a, **k):
            return HTTPResponse(404, b"", {}, "http://x.test/robots.txt")

    assert RobotsChecker(UA, transport=FakeTransport()).check("http://x.test/page").allowed is True


@pytest.mark.parametrize("status", [403, 500])
def test_robots_restricted_or_unverifiable_means_not_allowed(status):
    class FakeTransport:
        def request(self, *a, **k):
            return HTTPResponse(status, b"", {}, "http://x.test/robots.txt")

    assert RobotsChecker(UA, transport=FakeTransport()).check("http://x.test/page").allowed is False


UNSTOP_LIKE = """User-agent: *
Allow: /hackathons/
Allow: /api/public/*
Disallow: /api/*
Disallow: /competitions/*/register
Disallow: /files/*.pdf$
Disallow: /u/*

User-agent: BadBot
Disallow: /
"""


class _FakeTransport:
    def __init__(self, text):
        self.text = text

    def request(self, *a, **k):
        class R:
            status = 200
            text = self.text

        return R()


@pytest.mark.parametrize("path,allowed", [
    ("/hackathons/foo-1", True),
    ("/api/public/opportunity/search-result?page=2", True),  # longer Allow beats Disallow /api/*
    ("/api/private/x", False),
    ("/competitions/abc-123/register", False),  # wildcard in the middle (stdlib parser gets this wrong)
    ("/competitions/abc-123", True),
    ("/files/report.pdf", False),  # '$' end anchor
    ("/files/report.pdf.html", True),
    ("/u/someone", False),
])
def test_robots_wildcards_and_anchors(path, allowed):
    checker = RobotsChecker(UA, transport=_FakeTransport(UNSTOP_LIKE))
    assert checker.check(f"https://x.test{path}").allowed is allowed


def test_robots_stdlib_parser_would_get_wildcard_wrong():
    """Documents why we don't use urllib.robotparser."""
    from urllib.robotparser import RobotFileParser

    rp = RobotFileParser()
    rp.parse(UNSTOP_LIKE.splitlines())
    assert rp.can_fetch(UA, "https://x.test/competitions/abc-123/register") is True  # wrong!


def test_robots_specific_agent_group_overrides_star():
    checker = RobotsChecker("BadBot/1.0", transport=_FakeTransport(UNSTOP_LIKE))
    assert checker.check("https://x.test/hackathons/foo").allowed is False


def test_robots_empty_disallow_allows_everything():
    checker = RobotsChecker(UA, transport=_FakeTransport("User-agent: *\nDisallow:\n"))
    assert checker.check("https://x.test/anything").allowed is True


def test_robots_is_cached_per_origin(server, transport, hits):
    checker = RobotsChecker(UA, transport=transport)
    checker.check(f"{server}/ok")
    checker.check(f"{server}/private/x")
    assert hits == {"/robots.txt": 1}



def test_tos_flag_blocks_source():
    ok, _ = TosChecker().check(Source("a", "http://x", "static", tos_allows_scraping=True))
    assert ok
    ok, reason = TosChecker().check(Source("a", "http://x", "static", tos_allows_scraping=False, tos_note="no bots"))
    assert not ok and "no bots" in reason


def test_rate_limiter_waits_between_requests_to_same_host():
    now = [0.0]
    slept = []

    def fake_sleep(s):
        slept.append(s)
        now[0] += s

    rl = RateLimiter(1.0, 2.0, sleep=fake_sleep, clock=lambda: now[0], rand=lambda a, b: 1.5)
    rl.wait("http://a.test/1")  # first request: no wait
    rl.wait("http://a.test/2")  # second: must wait 1.5s
    rl.wait("http://b.test/1")  # other host: no wait
    assert slept == [1.5]
