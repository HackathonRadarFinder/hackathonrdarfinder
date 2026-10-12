"""Terms-of-Service gate.

ToS cannot be machine-verified, so the decision is made by a human and recorded in
sources.json: set `"tos_allows_scraping": true` only after recording permission. Missing or
false permission skips the source before any network activity.
"""
from __future__ import annotations

from ..models import Source
from ..monitoring.logger import get_logger

log = get_logger("tos")


class TosChecker:
    def check(self, source: Source) -> tuple[bool, str]:
        if source.tos_allows_scraping:
            return True, "ToS flag allows scraping"
        reason = f"ToS permission not granted for automated scraping: {source.tos_note or 'no note given'}"
        log.warning("tos_skip source_id=%s reason=%s", source.source_id, reason)
        return False, reason
