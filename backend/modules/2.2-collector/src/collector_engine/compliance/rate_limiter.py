"""Polite rate limiting: 1-2 seconds between requests to the same host, strictly sequential."""
from __future__ import annotations

import random
import time
from typing import Callable
from urllib.parse import urlsplit

from ..monitoring.logger import get_logger

log = get_logger("ratelimit")


class RateLimiter:
    def __init__(
        self,
        min_delay: float = 1.0,
        max_delay: float = 2.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        rand: Callable[[float, float], float] = random.uniform,
    ):
        if min_delay < 0 or max_delay < min_delay:
            raise ValueError("require 0 <= min_delay <= max_delay")
        self.min_delay, self.max_delay = min_delay, max_delay
        self._sleep, self._clock, self._rand = sleep, clock, rand
        self._last: dict[str, float] = {}

    def wait(self, url: str) -> float:
        """Block until it is polite to hit this URL's host again. Returns seconds slept."""
        host = urlsplit(url).netloc
        slept = 0.0
        last = self._last.get(host)
        if last is not None:
            gap = self._rand(self.min_delay, self.max_delay)
            slept = max(0.0, gap - (self._clock() - last))
            if slept > 0:
                log.debug("rate_limit host=%s sleeping=%.2fs", host, slept)
                self._sleep(slept)
        self._last[host] = self._clock()
        return slept
