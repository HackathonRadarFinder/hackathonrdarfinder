"""Manually approved Unstop/Devfolio CSV -> existing Hackathon Radar DB.

Place in backend/workers. Run from backend/ after Alembic migrations.
No network requests; dry-run by default; will not overwrite existing event URLs.
This is a manual MVP bridge, not a substitute for live governed discovery runs.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from typing import NamedTuple

from sqlalchemy import select

from radar_collector.radar_scraper import clean_url, source_for

from app.core.database import SessionLocal
from app.models.core import EventVersion
from app.models.hackathon import Hackathon
from app.models.organization import Organization
from app.schemas.event import EventCreate
from app.services.duplicate_review import merged_alias_id

ACCEPT = ("title", "organization", "start_date", "end_date", "registration_deadline",
          "location", "mode", "prize", "description", "url", "source", "scraped_at")


class ReviewedRecord(NamedTuple):
    event: EventCreate
    source_hash: str
    date_precision: str
    collection_mode: str
    permission_reference: str
    acquisition_evidence: dict | None = None


def approved_source(url: str, source: str) -> bool:
    try:
        if any(ord(c) <= 32 or ord(c) == 127 for c in url) or urlsplit(url).fragment:
            return False
        return source in {"Unstop", "Devfolio"} and source_for(url) == source
    except (ValueError, TypeError):
        return False


def validate_approved(record: ReviewedRecord) -> ReviewedRecord:
    event = EventCreate.model_validate(record.event.model_dump())
    if not approved_source(str(event.url or ""), event.source):
        raise ValueError("URL/source mismatch")
    if event.organization_id is not None or not event.organization or not event.scraped_at or not event.description:
        raise ValueError("Missing required reviewed event data")
    if record.collection_mode == "brabble_api":
        from app.services.brabble_adapter import validate_evidence, VERIFICATIONS
        evidence = validate_evidence(record.acquisition_evidence)
        if record.source_hash:
            raise ValueError("API evidence must not claim a source HTML hash")
        if not VERIFICATIONS.issubset(set(evidence.get("verified_fields", []))):
            raise ValueError("Brabble organizer, URL and date review is required")
        raw = evidence["raw_record"]
        if event.source != raw["platform"]:
            raise ValueError("API original platform mismatch")
        if event.organization.casefold() in {"see listing", "unknown", "n/a"}:
            raise ValueError("A verified organizer is required")
        from app.services.review_evidence import validate_review
        validate_review(event, evidence, record.date_precision)
    elif not re.fullmatch(r"[0-9a-f]{64}", record.source_hash):
        raise ValueError("Missing source HTML SHA-256")
    if record.date_precision not in {"unknown", "day", "exact"}:
        raise ValueError("Invalid date precision")
    if record.collection_mode not in {"live_public", "reviewed_manual", "brabble_api"}:
        raise ValueError("Only real, authorized collection can be approved; fixtures cannot be imported")
    if not record.permission_reference.strip() or len(record.permission_reference) > 1000:
        raise ValueError("Documented source permission reference required")
    payload = event.model_dump()
    payload["url"] = clean_url(str(event.url))
    return record._replace(event=EventCreate.model_validate(payload))


def load_approved(csv_file: Path):
    if csv_file.stat().st_size > 2_000_000:
        raise ValueError("CSV exceeds 2 MB manual review limit")
    approved, skipped = [], 0
    with csv_file.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames and len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Duplicate CSV headers")
        if not reader.fieldnames or not {"url", "title", "organization", "source", "review_status"}.issubset(reader.fieldnames):
            raise ValueError("Not a candidate CSV from radar_scraper.py")
        for i, row in enumerate(reader, 1):
            if None in row or None in row.values():
                raise ValueError(f"Row {i}: malformed CSV column count")
            if i > 1000: raise ValueError("Max 1000 CSV records per import")
            if row.get("review_status", "").strip().lower() != "approved":
                skipped += 1
                continue
            if not approved_source(row.get("url", ""), row.get("source", "")):
                raise ValueError(f"Row {i}: URL/source mismatch")
            # Reverse the exporter Excel-formula safety prefix, if present.
            payload = {}
            for key in ACCEPT:
                value = row.get(key) or None
                if isinstance(value, str) and value.startswith("'") and value[1:].lstrip().startswith(("=", "+", "-", "@")):
                    value = value[1:]
                payload[key] = value
            event = EventCreate.model_validate(payload)
            if not event.organization or not event.url or not event.scraped_at or not event.description:
                raise ValueError(f"Row {i}: missing required data for manual approval")
            hashval = row.get("source_hash", "")
            if row.get("collection_mode") != "brabble_api" and not re.fullmatch(r"[0-9a-f]{64}", hashval):
                raise ValueError(f"Row {i}: missing source HTML SHA-256")
            approved.append(validate_approved(ReviewedRecord(
                event, hashval, row.get("date_precision", "unknown"),
                row.get("collection_mode", ""), row.get("permission_reference", ""),
                json.loads(row["acquisition_evidence"]) if row.get("acquisition_evidence") else None)))
    return approved, skipped


def _stage(db, approved, reviewer: str):
    inserted = duplicate = 0
    urls = set()
    # Compare normalized legacy URLs without rewriting their source records.
    existing_urls = set()
    for stored in db.scalars(select(Hackathon.url)).all():
        if stored:
            try:
                existing_urls.add(clean_url(stored))
            except ValueError:
                pass
    provider_ids = set()
    for reviewed in approved:
        event, sha, precision, collection_mode, permission_reference, evidence = reviewed
        url = str(event.url)
        if merged_alias_id(db, url) is not None:
            duplicate += 1
            continue
        provider_key = (event.source, evidence['provider_id']) if evidence else None
        if url in urls or clean_url(url) in existing_urls or (provider_key and provider_key in provider_ids):
            duplicate += 1
            continue
        urls.add(url)
        # A provider ID survives slug/URL changes on refresh. Preserve the existing
        # event and its review history instead of silently replacing it.
        if evidence and db.scalar(select(EventVersion.id).where(
                EventVersion.changes['acquisition']['provider'].as_string() == 'Brabble.ai',
                EventVersion.changes['acquisition']['provider_id'].as_string() == evidence['provider_id'],
                EventVersion.changes['acquisition']['original_platform'].as_string() == event.source,
        ).limit(1)) is not None:
            duplicate += 1
            continue
        if provider_key:
            provider_ids.add(provider_key)
        org = db.scalar(select(Organization).where(Organization.name == event.organization))
        if org is None:
            org = Organization(name=event.organization)
            db.add(org)
            db.flush()
        values = event.model_dump(exclude={"organization", "organization_id"})
        values.update(organization_id=org.id, url=url)
        record = Hackathon(**values)
        db.add(record)
        db.flush()
        snapshot = {key: getattr(record, key) for key in ACCEPT if key not in {"organization", "organization_id"}}
        snapshot["organization"] = event.organization
        snapshot = {key: val.isoformat() if isinstance(val, datetime) else val for key, val in snapshot.items()}
        db.add(EventVersion(hackathon_id=record.id, version_number=1, snapshot=snapshot,
                            title=event.title, description=(event.description or "")[:1000],
                            changes={"fields": list(snapshot), "manual_reviewer": reviewer,
                                     **({"acquisition": evidence} if evidence else {"source_html_sha256": sha}),
                                     "date_precision": precision,
                                     "collection_mode": collection_mode, "permission_reference": permission_reference,
                                     "reviewed_at": datetime.now(timezone.utc).isoformat(),
                                     "importer": "import_reviewed_public-v2"}))
        inserted += 1
    return {"inserted": inserted, "duplicate_urls": duplicate}


def stage(db, approved, reviewer: str):
    """Validate before writes; stage atomically, leaving commit to the caller.

    SQLite serializes writers before duplicate reads. PostgreSQL serializes
    writes to the event table. No URL uniqueness migration is assumed.
    """
    if not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer) > 100:
        raise ValueError("A reviewer identifier of 1 to 100 characters is required")
    if not isinstance(approved, list) or len(approved) > 1000:
        raise ValueError("Expected at most 1000 reviewed records")
    records = [validate_approved(record) for record in approved]
    if db.new or db.dirty or db.deleted:
        raise ValueError("Use a clean session for reviewed ingestion")
    connection = db.connection()
    if connection.dialect.name == "sqlite":
        if not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
    elif connection.dialect.name == "postgresql":
        if connection.get_isolation_level() != 'READ COMMITTED':
            raise ValueError('Reviewed PostgreSQL ingestion requires READ COMMITTED isolation')
        connection.exec_driver_sql("LOCK TABLE hackathons IN SHARE ROW EXCLUSIVE MODE")
    else:
        raise ValueError("Reviewed ingestion requires SQLite or PostgreSQL writer serialization")
    with db.begin_nested():
        result = _stage(db, records, reviewer.strip())
        db.flush()  # Include provenance failures in the batch savepoint.
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_file", type=Path)
    ap.add_argument("--apply", action="store_true", help="Actually write approved rows to configured DB")
    ap.add_argument("--reviewed-by", default="", help="Required when --apply, operator applying the reviewed CSV")
    ap.add_argument('--check-target', action='store_true', help='Inspect redacted configuration only; never connect')
    ap.add_argument('--expect-database', help='Exact development database name or SQLite path required for --apply')
    args = ap.parse_args()
    if args.apply and not args.reviewed_by.strip():
        ap.error("--apply requires --reviewed-by")
    try:
        from app.core.config import settings
        from app.services.development_target import inspect_target, require_development_target
        if args.check_target:
            print(json.dumps(inspect_target(settings.DATABASE_URL, settings.ENVIRONMENT, args.expect_database)))
            return 0
        approved, skipped = load_approved(args.csv_file)
        if not args.apply:
            print(json.dumps({"approved_and_valid": len(approved), "not_approved": skipped, "applied": False}))
            return 0
        require_development_target(settings.DATABASE_URL, settings.ENVIRONMENT, args.expect_database)
        if any(record.acquisition_evidence and record.acquisition_evidence.get('review', {}).get('reviewer_type')
               == 'test_fixture' for record in approved):
            raise ValueError('Test review fixtures cannot be applied to a development database')
        from app.services.review_evidence import require_human_approval
        for record in approved:
            require_human_approval(record)
        with SessionLocal.begin() as db:
            result = stage(db, approved, args.reviewed_by.strip()[:100])
        print(json.dumps({**result, "not_approved": skipped, "applied": True}))
        return 0
    except Exception as exc:
        print(f"No batch committed: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
