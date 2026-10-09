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

    It must not do robots.txt / ToS checks, rate limiting or retries - the CollectorManager
    applies those around every collector so none can be skipped by accident.
    """

    collector_type: str = ""

    def __init__(self, settings: Settings):
        self.settings = settings

    @abstractmethod
    def fetch(self, source: Source) -> FetchResponse:
        """Fetch the source. Raise TemporaryFetchError / PermanentFetchError / BlockedError."""
