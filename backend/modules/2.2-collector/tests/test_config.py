import json

import pytest

from collector_engine.collectors.dynamic_collector import DynamicCollector
from collector_engine.collectors.registry import get_collector_class, register_collector
from collector_engine.collectors.static_collector import StaticCollector
from collector_engine.collectors.base_collector import BaseCollector
from collector_engine.config.loader import ConfigError, load_sources


def write(tmp_path, data):
    p = tmp_path / "sources.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_loads_sources_json_and_only_enabled(tmp_path):
    p = write(tmp_path, {"sources": [
        {"source_id": "a", "url": "https://example.com", "type": "static", "enabled": True},
        {"source_id": "b", "url": "https://example.com/js", "type": "dynamic", "enabled": True,
         "wait_for_selector": ".x"},
        {"source_id": "c", "url": "https://example.com/off", "type": "static", "enabled": False},
    ]})
    sources = load_sources(p)
    assert [s.source_id for s in sources] == ["a", "b"]
    assert sources[1].options == {"wait_for_selector": ".x"}
    assert len(load_sources(p, enabled_only=False)) == 3


def test_repo_sources_json_is_valid():
    from pathlib import Path

    assert load_sources(Path(__file__).parents[1] / "config" / "sources.json")


@pytest.mark.parametrize("bad", [
    {"sources": [{"url": "https://x.com", "type": "static"}]},  # no source_id
    {"sources": [{"source_id": "a", "url": "ftp://x.com", "type": "static"}]},  # bad scheme
    {"sources": [{"source_id": "../a", "url": "https://x.com", "type": "static"}]},  # path traversal
    {"sources": [{"source_id": "a", "url": "https://x.com", "type": "static"},
                 {"source_id": "a", "url": "https://y.com", "type": "static"}]},  # duplicate
    {"nope": []},
])
def test_invalid_config_is_rejected(tmp_path, bad):
    with pytest.raises(ConfigError):
        load_sources(write(tmp_path, bad))


def test_missing_file(tmp_path):
    with pytest.raises(ConfigError):
        load_sources(tmp_path / "missing.json")


def test_type_selects_static_vs_dynamic_collector():
    assert get_collector_class("static") is StaticCollector
    assert get_collector_class("dynamic") is DynamicCollector
    with pytest.raises(KeyError):
        get_collector_class("carrier-pigeon")


def test_new_collector_can_be_registered_without_touching_manager():
    class Custom(BaseCollector):
        def fetch(self, source):
            raise NotImplementedError

    register_collector("custom", Custom)
    assert get_collector_class("custom") is Custom
