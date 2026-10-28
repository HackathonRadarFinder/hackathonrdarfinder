"""Base class every collector implements."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..config.loader import Settings
from ..models import (
    BlockedError,
    FetchResponse,
    PermanentFetchError,
    Source,
    TemporaryFetchError,
)

# Markers of challenge / anti-bot pages. We never solve or bypass these - we report "blocked".
_BLOCK_MARKERS = (
    "g-recaptcha",
    "h-captcha",
    "cf-challenge",
    "cf-turnstile",
    "attention required! | cloudflare",
)


def check_status(status: int, url: str = "") -> None:
    """Translate an HTTP status into the right exception (no-op for 2xx/3xx)."""
    if status < 400:
        return
    if status in (401, 403, 429):
        raise BlockedError(f"Access refused with HTTP {status} for {url}")
    if status == 408 or status >= 500:
        raise TemporaryFetchError(f"Temporary HTTP {status} for {url}")
    raise PermanentFetchError(f"HTTP {status} for {url}")


def check_not_challenge(content: str, url: str = "") -> None:
    """Raise BlockedError if the page is a CAPTCHA / bot-challenge page."""
    lowered = content[:200_000].lower()
    for marker in _BLOCK_MARKERS:
        if marker in lowered:
            raise BlockedError(f"Anti-bot/CAPTCHA challenge detected ({marker}) at {url}")


class BaseCollector(ABC):
    """A collector fetches ONE source and returns raw content.

    Content requests use the governed transport and authorization hook. Standalone
    collectors build an equally governed context for the source origin.
    """

    collector_type: str = ""

    def __init__(self, settings: Settings, transport=None, authorize=None):
        self.settings = settings
        self.transport = transport
        self.authorize = authorize

    def request_context(self, source):
        from ..network import HttpTransport, URLPolicy
        from ..compliance.rate_limiter import RateLimiter
        from ..compliance.robots_checker import RobotsChecker

        transport = self.transport
        if transport is None:
            limiter = RateLimiter(self.settings.min_delay, self.settings.max_delay)
            transport = HttpTransport(
                URLPolicy([source.url]), timeout=self.settings.request_timeout,
                max_bytes=self.settings.max_response_bytes,
                max_redirects=self.settings.max_redirects,
                max_job_seconds=self.settings.max_job_seconds, before_request=limiter.wait,
            )
        authorize = self.authorize
        if authorize is None:
            authorize = RobotsChecker(self.settings.user_agent, transport=transport,
                                      headers=self.settings.request_headers()).authorize
        return transport, authorize

    @abstractmethod
    def fetch(self, source: Source) -> FetchResponse:
        """Fetch the source. Raise TemporaryFetchError / PermanentFetchError / BlockedError."""
