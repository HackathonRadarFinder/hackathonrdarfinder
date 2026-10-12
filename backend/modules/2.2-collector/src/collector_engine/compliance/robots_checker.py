"""Fail-closed robots authorization using the bounded, origin-restricted transport."""
from urllib.parse import urlsplit

from ..models import CollectorError, ComplianceError, RobotsResult
from ..network import HttpTransport, URLPolicy, origin_for_url
from .robots_rules import is_allowed, parse_robots


class RobotsChecker:
    def __init__(self, user_agent, timeout=15.0, transport=None, before_request=None, headers=None):
        self.user_agent = user_agent
        self.headers = headers or {"User-Agent": user_agent}
        self.timeout = timeout
        self.transport = transport
        self.before_request = before_request
        self._cache = {}

    def check(self, url):
        origin = origin_for_url(url)
        if origin not in self._cache:
            self._cache[origin] = self._load(origin)
        rules, base = self._cache[origin]
        if rules is None:
            return base
        parts = urlsplit(url)
        target = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        allowed = is_allowed(rules, target)
        return RobotsResult(allowed, "allowed by robots.txt" if allowed else
                            "disallowed by robots.txt for our User-Agent",
                            base.robots_url, base.robots_status)

    def authorize(self, url):
        result = self.check(url)
        if not result.allowed:
            raise ComplianceError(result.reason)

    def _load(self, origin):
        robots_url = f"{origin}/robots.txt"
        transport = self.transport or HttpTransport(
            URLPolicy([origin]), timeout=self.timeout, before_request=self.before_request)

        def robots_resource_only(url):
            # Robots verification must not become an unauthorised content fetch.
            if origin_for_url(url) != origin or urlsplit(url).path != "/robots.txt":
                raise ComplianceError("robots.txt redirect leaves the permitted robots resource")

        try:
            response = transport.request(robots_url, headers=self.headers, authorize=robots_resource_only)
        except CollectorError as exc:
            return None, RobotsResult(False,
                f"robots.txt unverifiable ({type(exc).__name__}); not scraping", robots_url)
        status = response.status
        if status == 200:
            return parse_robots(response.text, self.user_agent), RobotsResult(
                True, "robots.txt parsed", robots_url, status)
        if status in (404, 410):
            return None, RobotsResult(True, f"no robots.txt (HTTP {status}); allowed", robots_url, status)
        return None, RobotsResult(False,
            f"robots.txt returned HTTP {status}; cannot verify, not scraping", robots_url, status)
