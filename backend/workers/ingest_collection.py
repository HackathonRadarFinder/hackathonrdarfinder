"""Offline collector handoff. One writer per source; never fetches a website."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", required=True)
    parser.add_argument("--location", required=True, help="Relative collector .meta.json location")
    args = parser.parse_args(argv)
    collector = Path(__file__).resolve().parents[1] / "modules" / "2.2-collector" / "src"
    sys.path.insert(0, str(collector))
    from collector_engine.storage.local_storage import LocalRawStorage
    from app.services.scraper_ingestion import normalize_unstop_collection, ingest_events
    from app.core.database import SessionLocal
    try:
        record = LocalRawStorage(args.storage_root).load(args.location)
        normalized = normalize_unstop_collection(record)
        with SessionLocal() as db:
            result = ingest_events(db, normalized.events)
            db.commit()
        print(json.dumps({**asdict(result), "rejected": normalized.rejected}))
        return 0
    except Exception:
        # No paths, source content, SQL or connection strings in operational output.
        print("Collection ingestion failed; database transaction rolled back.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
