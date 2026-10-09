"""robots.txt compliance check, run by the manager before every collection."""
from __future__ import annotations

from typing import Callable, Optional
from urllib.parse import urlsplit

import requests

from ..models import RobotsResult
from ..monitoring.logger import get_logger
from .robots_rules import Rule, is_allowed, parse_robots

log = get_logger("robots")


class RobotsChecker:
    """Fetches robots.txt once per origin and answers "may our User-Agent fetch this URL?".

    Conservative rules (we err on the side of NOT scraping):
      * 200            -> parse and obey the rules
      * 404 / other 4xx-> no robots.txt published, everything allowed
      * 401 / 403      -> access restricted, treated as disallow-all
      * 5xx / network  -> cannot verify, treated as disallow-all
    """

    def __init__(
        self,
        user_agent: str,
        timeout: float = 15.0,
        session: Optional[requests.Session] = None,
        before_request: Optional[Callable[[str], None]] = None,
        headers: Optional[dict[str, str]] = None,
    ):
        self.user_agent = user_agent
        self.headers = headers or {"User-Agent": user_agent}
        self.timeout = timeout
        self.session = session or requests.Session()
        self.before_request = before_request  # e.g. rate limiter hook
        self._cache: dict[str, tuple[Optional[list[Rule]], RobotsResult]] = {}

    def check(self, url: str) -> RobotsResult:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._cache:
            self._cache[origin] = self._load(origin)
        rules, base = self._cache[origin]
        if rules is None:  # disallow-all or allow-all decided without rules
            return base
        target = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        if is_allowed(rules, target):
            result = RobotsResult(True, "allowed by robots.txt", base.robots_url, base.robots_status)
        else:
            result = RobotsResult(
                False, "disallowed by robots.txt for our User-Agent", base.robots_url, base.robots_status
            )
        log.info("robots_check url=%s allowed=%s reason=%s", url, result.allowed, result.reason)
        return result

    def _load(self, origin: str) -> tuple[Optional[RobotFileParser], RobotsResult]:
        robots_url = f"{origin}/robots.txt"
        if self.before_request:
            self.before_request(robots_url)
        try:
            resp = self.session.get(
                robots_url, headers=self.headers, timeout=self.timeout
            )
        except requests.RequestException as exc:
            log.warning("robots.txt unreachable url=%s error=%s -> treating as disallowed", robots_url, exc)
            return None, RobotsResult(False, f"robots.txt unreachable ({exc.__class__.__name__}); not scraping", robots_url)

        status = resp.status_code
        if status == 200:
            rules = parse_robots(resp.text, self.user_agent)
            return rules, RobotsResult(True, "robots.txt parsed", robots_url, status)
        if status in (401, 403):
            return None, RobotsResult(False, f"robots.txt returned HTTP {status}; access restricted", robots_url, status)
        if status >= 500:
            return None, RobotsResult(False, f"robots.txt returned HTTP {status}; cannot verify, not scraping", robots_url, status)
        return None, RobotsResult(True, f"no robots.txt (HTTP {status}); allowed", robots_url, status)
