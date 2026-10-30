"""Explicit opt-in discovery worker; no network or database work when disabled."""
import argparse
from datetime import datetime, timezone
import json
import os
import time
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--watch', action='store_true', help='Poll due schedules until Ctrl+C')
    parser.add_argument('--poll-seconds', type=int, default=30, choices=range(5, 61))
    parser.add_argument('--allow-live', action='store_true', help='Still requires recorded source permission and robots approval')
    parser.add_argument('--batch-size', type=int, default=10, choices=range(1, 101), help='Maximum due sources per pass; collection concurrency remains bounded at one')
    args = parser.parse_args()
    if os.environ.get('DISCOVERY_ENABLED', '').lower() != 'true':
        print(json.dumps({'enabled': False, 'executed': False})); return 0
    from app.core.database import SessionLocal
    from app.services.discovery_service import run_due, run_source
    try:
        while True:
            try:
                with SessionLocal() as db:
                    now = datetime.now(timezone.utc)
                    run_source(db, None, now)  # Recover abandoned PostgreSQL runs before selecting due sources.
                    results = run_due(db, now, allow_live=args.allow_live, limit=args.batch_size)
                Path(os.environ.get('COLLECTOR_HEARTBEAT', str(Path(tempfile.gettempdir()) / 'collector-heartbeat'))).write_text(str(time.time()))
            except Exception:
                results = {'worker': {'status': 'failed', 'error_code': 'database_or_worker_unavailable'}}
            print(json.dumps(results), flush=True)
            if not args.watch:
                return 1 if any(row['status'] == 'failed' for row in results.values()) else 0
            time.sleep(args.poll_seconds)
    except KeyboardInterrupt:
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
