"""Maps a source "type" from sources.json to a collector class.

Add a new collector by subclassing BaseCollector and calling register_collector("name", Class)
- no change to the manager is needed.
"""
from __future__ import annotations

from typing import Type

from .base_collector import BaseCollector
from .dynamic_collector import DynamicCollector
from .static_collector import StaticCollector

_REGISTRY: dict[str, Type[BaseCollector]] = {
    "static": StaticCollector,  # Scrapy - default choice
    "dynamic": DynamicCollector,  # Playwright - only when JS rendering is required
}


def register_collector(type_name: str, cls: Type[BaseCollector]) -> None:
    _REGISTRY[type_name.lower()] = cls


def get_collector_class(type_name: str) -> Type[BaseCollector]:
    try:
        return _REGISTRY[type_name.lower()]
    except KeyError:
        raise KeyError(f"Unknown collector type '{type_name}'. Known: {sorted(_REGISTRY)}") from None


def known_types() -> list[str]:
    return sorted(_REGISTRY)
