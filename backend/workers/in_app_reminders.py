"""Process saved-event in-app reminders; never contacts an email transport."""
import argparse
from datetime import datetime, timezone
import json
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--watch', action='store_true')
    parser.add_argument('--poll-seconds', type=int, default=60, choices=range(5, 61))
    parser.add_argument('--batch-size', type=int, default=100, choices=range(1, 1001))
    args = parser.parse_args()
    from app.core.database import SessionLocal
    from app.services.in_app_reminders import enqueue_in_app
    try:
        while True:
            with SessionLocal() as db:
                print(json.dumps(enqueue_in_app(db, datetime.now(timezone.utc), args.batch_size)), flush=True)
            if not args.watch:
                return 0
            time.sleep(args.poll_seconds)
    except KeyboardInterrupt:
        return 0
    except Exception:
        parser.exit(1, 'In-app reminder processing failed; no email transport was invoked.\n')


if __name__ == '__main__':
    raise SystemExit(main())
