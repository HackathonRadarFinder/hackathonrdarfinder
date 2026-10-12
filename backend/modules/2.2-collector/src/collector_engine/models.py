"""Data models and exceptions shared across Module 2.2."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

SOURCE_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", re.ASCII)


def validate_source_id(value: str) -> str:
    reserved = {"CON", "PRN", "AUX", "NUL"} | {f"{prefix}{n}" for prefix in ("COM", "LPT") for n in range(1, 10)}
    if (not isinstance(value, str) or not SOURCE_ID_PATTERN.fullmatch(value)
            or value.endswith(".") or value.split(".", 1)[0].upper() in reserved):
        raise ValueError("Invalid source_id: use a safe ASCII identifier of 1-100 characters")
    return value

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


class ComplianceError(PermanentFetchError):
    """An access-policy or robots decision prohibits a request."""


@dataclass
class Source:
    """One entry of config/sources.json."""

    source_id: str
    url: str
    type: str  # "static" | "dynamic" (or any collector registered later)
    enabled: bool = True
    # Permission must be explicitly recorded; missing or false permission skips the source.
    tos_allows_scraping: bool = False
    tos_note: str = ""
    # Collector-specific options; dynamic options are retained but never executed.
    options: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        validate_source_id(self.source_id)
        from .network import parsed_url
        parsed_url(self.url)
        if type(self.enabled) is not bool or type(self.tos_allows_scraping) is not bool:
            raise ValueError("enabled and tos_allows_scraping must be booleans")
        if not isinstance(self.type, str) or not self.type.strip():
            raise ValueError("type must be a nonempty string")
        self.type = self.type.strip().lower()
        if not isinstance(self.options, dict):
            raise ValueError("options must be an object")
        for key in ("max_load_more", "max_scrolls"):
            if key in self.options and (type(self.options[key]) is not int or not 0 <= self.options[key] <= 20):
                raise ValueError(f"{key} must be an integer from 0 to 20")
        if "scroll_to_end" in self.options and type(self.options["scroll_to_end"]) is not bool:
            raise ValueError("scroll_to_end must be a boolean")
        if "action_pause" in self.options:
            import math
            value = self.options["action_pause"]
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 10:
                raise ValueError("action_pause must be finite and between 0 and 10")
        for key in ("wait_for_selector", "load_more_selector", "item_selector"):
            if key in self.options and (not isinstance(self.options[key], str) or not 1 <= len(self.options[key]) <= 256):
                raise ValueError(f"{key} must be a string of 1-256 characters")


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
