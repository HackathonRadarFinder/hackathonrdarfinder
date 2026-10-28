"""Explicit, offline normalization and ingestion. Never opens or commits a database.

Run ingestion with one writer per source: the existing event table has no unique
URL constraint. Duplicates are skipped, never used to overwrite curated events.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from urllib.parse import urlsplit, urlunsplit

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.hackathon import Hackathon
from app.models.organization import Organization
from app.schemas.event import EventCreate
from scraper.unstop.scraper import normalise


@dataclass
class NormalizationResult:
    events: list[EventCreate]
    rejected: int = 0


@dataclass
class IngestionResult:
    inserted: int = 0
    duplicates: int = 0
    organizations_created: int = 0


def _unstop_url(value: str, *, api: bool = False) -> str:
    if not isinstance(value, str) or any(ord(c) < 33 or ord(c) == 127 for c in value):
        raise ValueError("Expected an HTTPS Unstop URL without whitespace or controls")
    parts = urlsplit(value)
    if (parts.scheme != "https" or parts.hostname != "unstop.com"
            or parts.username is not None or parts.password is not None
            or parts.port is not None or not parts.path.startswith("/")):
        raise ValueError("Expected an HTTPS Unstop URL without credentials or port")
    if api and parts.path != "/api/public/opportunity/search-result":
        raise ValueError("Unexpected raw collection URL")
    return urlunsplit(("https", "unstop.com", parts.path, parts.query, ""))


def _event(value: EventCreate | dict) -> EventCreate:
    if not isinstance(value, (EventCreate, dict)):
        raise ValueError("Expected an event object")
    data = value.model_dump(mode="json") if isinstance(value, EventCreate) else dict(value)
    if data.get("source") != "Unstop":
        raise ValueError("This adapter accepts Unstop records only")
    # A record must have a real organization name; do not invent a fallback or
    # trust an external integer as an internal organization identifier.
    if data.get("organization_id") is not None or not data.get("organization"):
        raise ValueError("A scraped organization name is required")
    data["url"] = _unstop_url(data.get("url") or "")
    return EventCreate.model_validate(data)


def normalize_unstop_collection(record: dict) -> NormalizationResult:
    """Convert a successful raw collector API page into validated event inputs.

    Invalid individual opportunities are counted and omitted. Invalid collection
    envelopes fail as a whole so callers cannot mistake a failed fetch for data.
    """
    if not isinstance(record, dict) or record.get("http_status") != 200:
        raise ValueError("Expected a successful Unstop API collection")
    if record.get("status", "success") != "success":
        raise ValueError("Cannot normalize an unsuccessful collection")
    _unstop_url(record.get("url") or "", api=True)
    _unstop_url(record.get("final_url") or record["url"], api=True)
    timestamp = record.get("fetched_at")
    if not isinstance(timestamp, str):
        raise ValueError("Collection timestamp must be an ISO-8601 string")
    fetched_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if fetched_at.tzinfo is None:
        raise ValueError("Collection timestamp must include its timezone")
    scraped_at = fetched_at.astimezone(timezone.utc).isoformat()
    raw = record.get("raw_content")
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > 5_000_000:
        raise ValueError("Raw collection must be JSON text within the size limit")
    payload = json.loads(raw)
    block = payload.get("data") if isinstance(payload, dict) else None
    items = block.get("data") if isinstance(block, dict) else None
    if not isinstance(items, list) or len(items) > 1000:
        raise ValueError("Unexpected Unstop API record list")
    result = NormalizationResult([])
    for item in items:
        try:
            normalized = normalise(item, scraped_at)
            if normalized is None:
                raise ValueError("Invalid opportunity")
            result.events.append(_event(normalized))
        except (ValidationError, ValueError, TypeError, OverflowError):
            result.rejected += 1
    return result


def ingest_events(db: Session, records: list[EventCreate | dict]) -> IngestionResult:
    """Stage a validated batch in a SAVEPOINT; the caller decides commit/rollback.

    Validation happens before writes. A failed batch rolls back its own changes
    without committing or discarding unrelated caller work. The caller must use
    a single ingestion writer until a separately reviewed uniqueness migration.
    """
    if not isinstance(records, list):
        raise ValueError("Ingestion batch must be a list")
    if len(records) > 1000:
        raise ValueError("Ingestion batch exceeds 1000 events")
    events = [_event(record) for record in records]
    if db.new or db.dirty or db.deleted:
        raise ValueError("Use a clean session for scraper ingestion")
    result = IngestionResult()
    seen = set()
    try:
        # Explicitly begin SQLite's real outer transaction before SAVEPOINT.
        # Legacy sqlite3 transaction mode otherwise releases a top-level
        # SAVEPOINT as a commit, defeating caller rollback.
        connection = db.connection()
        if connection.dialect.name == "sqlite":
            driver = connection.connection.driver_connection
            if not driver.in_transaction:
                connection.exec_driver_sql("BEGIN")
        with db.begin_nested():
            for event in events:
                url = str(event.url)
                key = (event.source, url)
                existing = db.scalar(select(Hackathon.id).where(
                    Hackathon.source == event.source, Hackathon.url == url,
                ).limit(1))
                if key in seen or existing is not None:
                    result.duplicates += 1
                    continue
                seen.add(key)
                organization = db.scalar(select(Organization).where(
                    Organization.name == event.organization,
                ))
                if organization is None:
                    organization = Organization(name=event.organization)
                    db.add(organization)
                    db.flush()
                    result.organizations_created += 1
                values = event.model_dump(exclude={"organization", "organization_id"})
                values.update(url=url, organization_id=organization.id)
                db.add(Hackathon(**values))
                db.flush()
                result.inserted += 1
    except SQLAlchemyError:
        raise AppException(
            code="DATABASE_ERROR", message="Unable to stage scraped events.", status_code=503,
        ) from None
    return result
