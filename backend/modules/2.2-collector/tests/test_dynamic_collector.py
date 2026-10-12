"""Dynamic collection is disabled until browser requests can be governed."""
import builtins

import pytest

from collector_engine.collectors.dynamic_collector import DynamicCollector
from collector_engine.models import BlockedError, Source


@pytest.mark.parametrize("options", [{}, {"wait_for_selector": ".q"},
                                     {"scroll_to_end": True, "max_scrolls": 3}])
def test_dynamic_refuses_before_browser_import_or_network(settings, server, hits, monkeypatch, options):
    original = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        assert not name.startswith(("playwright", "scrapy")), "disabled collectors must not load browser engines"
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    src = Source("dynamic", f"{server}/ok", "dynamic", tos_allows_scraping=True, options=options)
    with pytest.raises(BlockedError):
        DynamicCollector(settings).fetch(src)
    assert hits == {}
