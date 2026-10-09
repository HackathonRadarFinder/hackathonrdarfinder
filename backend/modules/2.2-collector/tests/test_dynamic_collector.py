import pytest

from collector_engine.collectors.dynamic_collector import DynamicCollector
from collector_engine.models import BlockedError, Source

pytest.importorskip("playwright")


def dyn(server, path, **opts):
    return Source("d", f"{server}{path}", "dynamic", options={"action_pause": 0.3, **opts})


def test_dynamic_collection_success(server, settings):
    resp = DynamicCollector(settings).fetch(dyn(server, "/ok"))
    assert resp.http_status == 200
    assert "Hello static" in resp.content


def test_javascript_rendered_content_is_captured(server, settings):
    resp = DynamicCollector(settings).fetch(dyn(server, "/js", wait_for_selector=".q"))
    assert "rendered by javascript" in resp.content
    assert "loading..." not in resp.content


def test_static_fetch_misses_js_content_but_dynamic_gets_it(server, settings):
    # Demonstrates why the dynamic collector exists.
    from collector_engine.collectors.static_collector import StaticCollector

    static = StaticCollector(settings).fetch(Source("s", f"{server}/js", "static"))
    assert 'id="c">loading...</div>' in static.content  # placeholder only; JS never ran
    dynamic = DynamicCollector(settings).fetch(dyn(server, "/js", wait_for_selector=".q"))
    assert 'id="c">loading...</div>' not in dynamic.content
    assert '<p class="q">rendered by javascript</p></div>' in dynamic.content


def test_load_more_button_is_clicked_until_gone(server, settings):
    resp = DynamicCollector(settings).fetch(dyn(server, "/loadmore", load_more_selector="#more"))
    assert resp.content.count('class="item"') == 9


def test_infinite_scroll_loads_more_items(server, settings):
    resp = DynamicCollector(settings).fetch(dyn(server, "/scroll", scroll_to_end=True, max_scrolls=6))
    assert resp.content.count('class="item"') > 3


def test_dynamic_403_is_blocked(server, settings):
    with pytest.raises(BlockedError):
        DynamicCollector(settings).fetch(dyn(server, "/forbidden"))
