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


@pytest.mark.parametrize("permission", [None, False, True])
def test_permission_defaults_false_and_preserves_booleans(tmp_path, permission):
    raw = {"source_id": "a", "url": "https://fixture.test", "type": "static"}
    if permission is not None:
        raw["tos_allows_scraping"] = permission
    assert load_sources(write(tmp_path, {"sources": [raw]}))[0].tos_allows_scraping is (permission is True)


@pytest.mark.parametrize("key", ["enabled", "tos_allows_scraping"])
@pytest.mark.parametrize("value", ["false", "true", 0, 1, None, [], {}])
def test_config_rejects_coerced_booleans(tmp_path, key, value):
    raw = {"source_id": "a", "url": "https://fixture.test", "type": "static", key: value}
    with pytest.raises(ConfigError):
        load_sources(write(tmp_path, {"sources": [raw]}))


@pytest.mark.parametrize("kwargs", [
    {"max_response_bytes": 0}, {"max_response_bytes": True}, {"max_response_bytes": 10_000_001},
    {"max_redirects": -1}, {"max_redirects": 11}, {"max_redirects": 1.5},
    {"request_timeout": float("nan")}, {"max_job_seconds": float("inf")},
    {"max_attempts": 0}, {"min_delay": -1}, {"min_delay": 3, "max_delay": 2},
    {"user_agent": "bot\r\nInjected: x"},
])
def test_settings_validate_bounds(kwargs):
    from collector_engine.config.loader import Settings
    with pytest.raises(ConfigError):
        Settings(**kwargs)


def test_settings_load_transport_and_backoff_environment(monkeypatch):
    from collector_engine.config.loader import Settings
    for key, value in {"MAX_RESPONSE_BYTES": "4096", "MAX_REDIRECTS": "2",
                       "MAX_JOB_SECONDS": "40", "BACKOFF_FACTOR": "3"}.items():
        monkeypatch.setenv(f"COLLECTOR_{key}", value)
    settings = Settings.from_env()
    assert (settings.max_response_bytes, settings.max_redirects,
            settings.max_job_seconds, settings.backoff_factor) == (4096, 2, 40, 3)


@pytest.mark.parametrize("value", ["false", "1.5", "", "-1"])
def test_invalid_environment_limits_raise_config_error(monkeypatch, value):
    from collector_engine.config.loader import Settings
    monkeypatch.setenv("COLLECTOR_MAX_RESPONSE_BYTES", value)
    with pytest.raises(ConfigError):
        Settings.from_env()


def test_cli_reports_environment_configuration_error(monkeypatch, capsys):
    from collector_engine.main import main
    monkeypatch.setenv("COLLECTOR_MAX_REDIRECTS", "bad")
    assert main([]) == 2
    assert "Config error" in capsys.readouterr().err
