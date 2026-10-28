"""Retry with exponential backoff for temporary failures only."""
from __future__ import annotations

import time
from typing import Callable, TypeVar

from .models import TemporaryFetchError
from .monitoring.logger import get_logger

log = get_logger("retry")
T = TypeVar("T")


def retry_call(
    func: Callable[[], T],
    max_attempts: int = 3,
    base_delay: float = 2.0,
    factor: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
    label: str = "",
) -> tuple[T, int]:
    """Call func up to max_attempts times. Returns (result, attempts_used).

    Only TemporaryFetchError is retried (delays: base, base*factor, ...). Every other
    exception - BlockedError, PermanentFetchError, anything unexpected - propagates at once.
    The raised exception gets an `.attempts` attribute with the number of attempts made.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            return func(), attempt
        except TemporaryFetchError as exc:
            exc.attempts = attempt  # type: ignore[attr-defined]
            if attempt >= max_attempts:
                log.error("retry_exhausted %s attempts=%d error=%s", label, attempt, exc)
                raise
            delay = base_delay * factor ** (attempt - 1)
            log.warning(
                "retry %s attempt=%d/%d failed: %s; backing off %.1fs",
                label, attempt, max_attempts, exc, delay,
            )
            sleep(delay)
        except Exception as exc:
            exc.attempts = attempt  # type: ignore[attr-defined]
            raise
