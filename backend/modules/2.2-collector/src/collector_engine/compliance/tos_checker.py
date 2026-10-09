"""Terms-of-Service gate.

ToS cannot be machine-verified, so the decision is made by a human and recorded in
sources.json: set `"tos_allows_scraping": false` (and a `tos_note`) for any site whose
terms prohibit automated access. Such sources are skipped and logged, never scraped.
"""
from __future__ import annotations

from ..models import Source
from ..monitoring.logger import get_logger

log = get_logger("tos")


class TosChecker:
    def check(self, source: Source) -> tuple[bool, str]:
        if source.tos_allows_scraping:
            return True, "ToS flag allows scraping"
        reason = f"ToS prohibits automated scraping: {source.tos_note or 'no note given'}"
        log.warning("tos_skip source_id=%s reason=%s", source.source_id, reason)
        return False, reason
