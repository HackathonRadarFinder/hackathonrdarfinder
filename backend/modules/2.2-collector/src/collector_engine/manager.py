"""CollectorManager: the single pipeline every source goes through.

  ToS gate -> robots.txt -> rate limit -> collector (with retry) -> storage -> log

Collectors receive a governed transport and pre-request robots authorization.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Callable, Optional

from .collectors.base_collector import BaseCollector
from .collectors.registry import get_collector_class
from .compliance.rate_limiter import RateLimiter
from .compliance.robots_checker import RobotsChecker
from .compliance.tos_checker import TosChecker
from .config.loader import Settings
from .items import count_items
from .models import (
    STATUS_BLOCKED,
    STATUS_FAILED,
    STATUS_SKIPPED,
    STATUS_SUCCESS,
    BlockedError,
    CollectionResult,
    ComplianceError,
    Source,
)
from .monitoring.alerts import Alerter
from .monitoring.logger import get_logger, job_summary
from .retry import retry_call
from .storage.base import RawStorage

log = get_logger("manager")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class CollectorManager:
    def __init__(
        self,
        settings: Settings,
        storage: RawStorage,
        robots: Optional[RobotsChecker] = None,
        rate_limiter: Optional[RateLimiter] = None,
        tos: Optional[TosChecker] = None,
        alerter: Optional[Alerter] = None,
        sleep: Callable[[float], None] = time.sleep,
        transport=None,
    ):
        self.settings = settings
        self.storage = storage
        self.rate_limiter = rate_limiter or RateLimiter(settings.min_delay, settings.max_delay)
        self.transport = transport
        self.robots = robots
        self.tos = tos or TosChecker()
        self.alerter = alerter or Alerter(settings.log_dir, settings.alert_webhook_url)
        self._sleep = sleep

    def run(self, sources: list[Source]) -> list[CollectionResult]:
        """Collect each source one after another (no concurrency, by design)."""
        results = [self.collect(s) for s in sources]
        counts = {}
        for r in results:
            counts[r.status] = counts.get(r.status, 0) + 1
        log.info("RUN_END total=%d %s", len(results), " ".join(f"{k}={v}" for k, v in sorted(counts.items())))
        return results

    def collect(self, source: Source) -> CollectionResult:
        result = CollectionResult(
            source_id=source.source_id, url=source.url, collector_type=source.type, started_at=_now()
        )
        log.info("JOB_START source_id=%s url=%s collector=%s", source.source_id, source.url, source.type)
        try:
            self._pipeline(source, result)
        except ComplianceError as exc:
            result.status = STATUS_SKIPPED
            result.robots_allowed = False
            result.robots_reason = str(exc)
            result.attempts = getattr(exc, "attempts", result.attempts)
        except BlockedError as exc:
            result.status, result.error = STATUS_BLOCKED, str(exc)
            result.attempts = getattr(exc, "attempts", result.attempts)
            log.warning("BLOCKED source_id=%s url=%s reason=%s", source.source_id, source.url, exc)
            self.alerter.blocked(result)
        except Exception as exc:  # temporary-exhausted, permanent, or unexpected
            result.status, result.error = STATUS_FAILED, f"{exc.__class__.__name__}: {exc}"
            result.attempts = getattr(exc, "attempts", result.attempts)
            log.error("FAILED source_id=%s url=%s error=%s", source.source_id, source.url, result.error)
        result.ended_at = _now()
        log.info(job_summary(result))
        return result

    def _pipeline(self, source: Source, result: CollectionResult) -> None:
        # 0. Resolve the collector first: an unknown type fails before any network traffic.
        collector_class = get_collector_class(source.type)

        # 1. Terms of Service gate
        tos_ok, tos_reason = self.tos.check(source)
        if not tos_ok:
            result.status, result.robots_reason = STATUS_SKIPPED, tos_reason
            log.warning("SKIPPED source_id=%s reason=%s", source.source_id, tos_reason)
            return

        # Dynamic collection refuses before even a robots request.
        if source.type == "dynamic":
            collector_class(self.settings).fetch(source)

        from .network import HttpTransport, URLPolicy
        transport = self.transport or HttpTransport(
            URLPolicy([source.url]), timeout=self.settings.request_timeout,
            max_bytes=self.settings.max_response_bytes, max_redirects=self.settings.max_redirects,
            max_job_seconds=self.settings.max_job_seconds, before_request=self.rate_limiter.wait,
        )
        # Injected transports also use the manager's limiter for every request.
        transport.before_request = self.rate_limiter.wait
        checker = self.robots or RobotsChecker(
            self.settings.user_agent, transport=transport, headers=self.settings.request_headers())
        collector: BaseCollector = collector_class(
            self.settings, transport=transport, authorize=checker.authorize)

        with transport.budget():
            self._collect_content(source, result, collector, checker, transport)

    def _collect_content(self, source, result, collector, checker, transport):

        # 2. robots.txt
        robots = checker.check(source.url)
        result.robots_allowed, result.robots_reason = robots.allowed, robots.reason
        if not robots.allowed:
            result.status = STATUS_SKIPPED
            log.warning("SKIPPED source_id=%s url=%s reason=%s", source.source_id, source.url, robots.reason)
            return

        # 3. Fetch with polite rate limiting + retry (temporary failures only)
        def attempt():
            return collector.fetch(source)

        def backoff(delay):
            remaining = transport.deadline - time.monotonic()
            if remaining <= 0:
                transport._remaining()
            self._sleep(min(delay, remaining))

        response, attempts = retry_call(
            attempt,
            max_attempts=self.settings.max_attempts,
            base_delay=self.settings.backoff_base,
            factor=self.settings.backoff_factor,
            sleep=backoff,
            label=f"source_id={source.source_id}",
        )
        result.attempts = attempts

        # 4. Fill result and store raw content + metadata
        result.status = STATUS_SUCCESS
        result.fetched_at = _now()
        result.http_status = response.http_status
        result.raw_content = response.content
        result.content_type = response.content_type
        result.final_url = response.final_url or source.url
        result.content_size = len(response.content.encode("utf-8"))
        result.item_count = count_items(
            response.content, response.content_type, source.options.get("item_selector")
        )
        self.storage.save(result)
