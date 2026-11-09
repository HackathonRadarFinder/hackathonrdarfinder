"""Bounded read-only startup gate. Never creates tables, imports or runs Alembic."""
import time

from app.core.database import engine
from app.core.exceptions import AppException
from app.services.readiness import check_readiness


def wait_until_ready(target=engine, *, attempts=3, delay=2, sleep=time.sleep):
    for attempt in range(attempts):
        try:
            check_readiness(target)
            return True
        except AppException as error:
            # Missing/stale migrations need explicit release authorization, not retries.
            if error.code == 'SCHEMA_NOT_READY' or attempt == attempts - 1:
                return False
            sleep(delay)
    return False


def main():
    if not wait_until_ready():
        print('Startup blocked: database unavailable or schema not current; no changes made.')
        return 1
    print('Startup readiness verified; no database changes made.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
