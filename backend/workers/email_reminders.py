"""One-shot worker: python -m workers.email_reminders --batch-size 100."""
import argparse
from datetime import datetime, timezone
import json

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.notification_service import dispatch_due, enqueue_due


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=100, choices=range(1, 1001), metavar="1..1000")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    if settings.EMAIL_MODE != "enabled":
        print(json.dumps({"mode": settings.EMAIL_MODE, "queued": 0, "accepted": 0}))
        return
    try:
        with SessionLocal() as db:
            queued = enqueue_due(db, now, args.batch_size)
            outcomes = dispatch_due(db, settings, now, args.batch_size,
                                    clock=lambda: datetime.now(timezone.utc))
        print(json.dumps({"queued": queued, "outcomes": outcomes}))
    except Exception:
        # No SQL/SMTP exception text or configuration values in console output.
        parser.exit(1, "Email reminder worker failed; inspect database state before retrying.\n")


if __name__ == "__main__":
    main()
