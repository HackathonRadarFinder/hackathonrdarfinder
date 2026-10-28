"""Storage interface. Implement this to move raw data to S3, a raw DB, etc."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import PurePosixPath
from abc import ABC, abstractmethod
from typing import Any

from ..models import CollectionResult, STATUS_SUCCESS, validate_source_id


class RawStorage(ABC):
    @abstractmethod
    def save(self, result: CollectionResult) -> str:
        """Persist raw content + metadata. Returns an opaque location string."""

    @abstractmethod
    def load(self, location: str) -> dict[str, Any]:
        """Return the Module 2.3 handoff record (incl. raw_content) saved at `location`."""

    @abstractmethod
    def list_locations(self, source_id: str | None = None) -> list[str]:
        """Locations of saved records, oldest first, optionally for one source."""


# ---- helpers shared by all backends, so every backend produces identical records ----

def require_storable(result: CollectionResult) -> None:
    validate_source_id(result.source_id)
    if result.status != STATUS_SUCCESS or not isinstance(result.raw_content, str) or not result.fetched_at:
        raise ValueError("Only successful collections (with raw_content) can be stored")
    datetime.fromisoformat(result.fetched_at.replace("Z", "+00:00"))


def validate_location(location: str) -> str:
    """Storage locations are relative POSIX keys, never filesystem expressions."""
    if not isinstance(location, str) or not location or "\\" in location or ":" in location:
        raise ValueError("Invalid storage location")
    parts = location.split("/")
    if PurePosixPath(location).is_absolute() or any(part in ("", ".", "..") for part in parts):
        raise ValueError("Invalid storage location")
    return location


def file_stamp(result: CollectionResult) -> str:
    """2026-10-07T10:30:00Z -> 20261007T103000Z"""
    return re.sub(r"[^0-9TZ]", "", result.fetched_at or "")


def raw_extension(result: CollectionResult) -> str:
    return "json" if "json" in result.content_type.lower() else "html"


def build_metadata(result: CollectionResult, raw_file: str) -> dict[str, Any]:
    meta = result.metadata_dict()
    meta["raw_file"] = raw_file
    return meta


def handoff_record(meta: dict[str, Any], raw_content: str) -> dict[str, Any]:
    """Module 2.3 record rebuilt from stored metadata + raw content."""
    return {
        "source_id": meta["source_id"],
        "fetched_at": meta["fetched_at"],
        "url": meta["url"],
        "http_status": meta["http_status"],
        "raw_content": raw_content,
        "collector_type": meta["collector_type"],
        "content_type": meta["content_type"],
        "content_size": meta["content_size"],
        "item_count": meta.get("item_count"),
        "final_url": meta["final_url"],
        "attempts": meta["attempts"],
    }
