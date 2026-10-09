"""Counts collected items for monitoring only. It does NOT extract or parse data (Module 2.3)."""
from __future__ import annotations

import json
from typing import Optional

from .monitoring.logger import get_logger

log = get_logger("items")


def count_items(content: str, content_type: str = "", selector: Optional[str] = None) -> Optional[int]:
    """Number of elements matching the CSS `selector`, or the length of a top-level JSON list.

    Returns None when it cannot be determined.
    """
    if selector:
        from parsel import Selector  # installed with Scrapy

        try:
            return len(Selector(text=content).css(selector))
        except Exception as exc:  # invalid selector must never break a collection
            log.warning("item_selector %r could not be applied: %s", selector, exc)
            return None
    if "json" in content_type.lower():
        try:
            data = json.loads(content)
        except ValueError:
            return None
        if isinstance(data, list):
            return len(data)
    return None
