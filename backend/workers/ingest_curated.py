"""Offline, operator-reviewed public facts; no crawling or permission bypass.

One writer only. Validate the complete batch before opening a database session.
No existing event is overwritten. --apply is required to commit.
"""
import argparse
import json
from pathlib import Path

from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.hackathon import Hackathon
from app.models.organization import Organization
from app.services.curated_validation import validate_records
from app.services.duplicate_review import merged_alias_id


def ingest(db, records):
    inserted = duplicates = 0
    for event in records:
        if merged_alias_id(db, str(event.url)) is not None:
            duplicates += 1
            continue
        if db.scalar(select(Hackathon.id).where(Hackathon.url == str(event.url))) is not None:
            duplicates += 1
            continue
        org = db.scalar(select(Organization).where(Organization.name == event.organization))
        if org is None:
            org = Organization(name=event.organization)
            db.add(org)
            db.flush()
        values = event.model_dump(exclude={"organization", "organization_id"})
        values.update(organization_id=org.id, url=str(event.url))
        db.add(Hackathon(**values))
        db.flush()
        inserted += 1
    return {"inserted": inserted, "duplicates": duplicates}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        if args.file.stat().st_size > 1_000_000:
            raise ValueError("Review file exceeds limit")
        records = validate_records(json.loads(args.file.read_text(encoding="utf-8")))
        if not args.apply:
            print(json.dumps({"validated": len(records), "applied": False}))
            return 0
        with SessionLocal() as db:
            result = ingest(db, records)
            db.commit()
        print(json.dumps(result))
        return 0
    except Exception:
        print("Curated ingestion failed; no batch was committed.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
