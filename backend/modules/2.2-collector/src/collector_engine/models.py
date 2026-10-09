"""Data models and exceptions shared across Module 2.2."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

SOURCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")

# CollectionResult.status values
STATUS_SUCCESS = "success"
STATUS_SKIPPED = "skipped"  # robots.txt / ToS said no; nothing was scraped
STATUS_BLOCKED = "blocked"  # site refused us (403/429/CAPTCHA); we do not bypass
STATUS_FAILED = "failed"  # technical failure after retries (or non-retryable error)


class CollectorError(Exception):
    """Base class for collection errors."""


class TemporaryFetchError(CollectorError):
    """Transient failure (timeout, connection error, 5xx). Worth retrying."""


class PermanentFetchError(CollectorError):
    """Failure that retrying will not fix (e.g. 404)."""


class BlockedError(CollectorError):
    """Access refused (401/403/429, CAPTCHA, anti-bot page). Never retried, never bypassed."""


@dataclass
class Source:
    """One entry of config/sources.json."""

    source_id: str
    url: str
    type: str  # "static" | "dynamic" (or any collector registered later)
    enabled: bool = True
    # Terms of Service: set to false if the site forbids automated access -> source is skipped.
    tos_allows_scraping: bool = True
    tos_note: str = ""
    # Collector-specific options (e.g. load_more_selector for dynamic sources).
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class FetchResponse:
    """What a collector returns for one successful fetch."""

    url: str
    http_status: int
    content: str
    content_type: str = ""
    final_url: str = ""


@dataclass
class RobotsResult:
    allowed: bool
    reason: str
    robots_url: str = ""
    robots_status: Optional[int] = None


@dataclass
class CollectionResult:
    """Outcome of one collection job. `handoff_dict()` is the Module 2.3 contract."""

    source_id: str
    url: str
    collector_type: str
    status: str = STATUS_FAILED
    started_at: str = ""
    ended_at: str = ""
    fetched_at: Optional[str] = None
    http_status: Optional[int] = None
    raw_content: Optional[str] = None
    content_type: str = ""
    content_size: int = 0  # bytes (UTF-8) of raw_content
    item_count: Optional[int] = None  # items counted via `item_selector` (or JSON list length)
    final_url: str = ""
    attempts: int = 0
    robots_allowed: Optional[bool] = None
    robots_reason: str = ""
    error: Optional[str] = None
    storage_location: Optional[str] = None

    def handoff_dict(self) -> dict[str, Any]:
        """Record handed to Module 2.3: the five required fields plus light metadata."""
        return {
            "source_id": self.source_id,
            "fetched_at": self.fetched_at,
            "url": self.url,
            "http_status": self.http_status,
            "raw_content": self.raw_content,
            "collector_type": self.collector_type,
            "content_type": self.content_type,
            "content_size": self.content_size,
            "item_count": self.item_count,
            "final_url": self.final_url,
            "attempts": self.attempts,
        }

    def metadata_dict(self) -> dict[str, Any]:
        """Everything except the (potentially large) raw content."""
        data = asdict(self)
        data.pop("raw_content")
        return data
