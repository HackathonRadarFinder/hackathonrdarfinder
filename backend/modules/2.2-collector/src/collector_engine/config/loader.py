"""Loads sources.json and runtime settings (.env / environment variables)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from ..models import SOURCE_ID_PATTERN, Source

DEFAULT_USER_AGENT = (
    "Module22Collector/1.0 (compliant research collector; "
    "contact: set COLLECTOR_USER_AGENT in .env)"
)


class ConfigError(Exception):
    """sources.json is missing or invalid."""


@dataclass
class Settings:
    user_agent: str = DEFAULT_USER_AGENT
    min_delay: float = 1.0  # seconds between requests to the same host
    max_delay: float = 2.0
    max_attempts: int = 3
    backoff_base: float = 2.0  # delays: 2s, 4s, ...
    backoff_factor: float = 2.0
    request_timeout: float = 30.0
    raw_data_dir: Path = Path("data/raw")
    log_dir: Path = Path("logs")
    log_level: str = "INFO"
    headless: bool = True  # False = show the Playwright browser window (debugging/demo)
    slow_mo_ms: int = 0  # headed only: slow every browser action so you can watch it
    hold_seconds: float = 0.0  # headed only: keep the window open this long before closing
    contact_email: str = ""  # sent as the `From:` header so site owners can reach us
    alert_webhook_url: str = ""  # optional Slack-style webhook, used when a source blocks us
    storage_backend: str = "local"  # "local" | "s3"
    s3_bucket: str = ""
    s3_prefix: str = "raw/"

    def request_headers(self) -> dict[str, str]:
        """Honest, identifying headers sent by every collector (no browser impersonation)."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en",
        }
        if self.contact_email:
            headers["From"] = self.contact_email
        return headers

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from environment variables (call load_dotenv() first if wanted)."""
        env = os.environ
        return cls(
            user_agent=env.get("COLLECTOR_USER_AGENT", DEFAULT_USER_AGENT),
            min_delay=float(env.get("COLLECTOR_MIN_DELAY", 1.0)),
            max_delay=float(env.get("COLLECTOR_MAX_DELAY", 2.0)),
            max_attempts=int(env.get("COLLECTOR_MAX_ATTEMPTS", 3)),
            backoff_base=float(env.get("COLLECTOR_BACKOFF_BASE", 2.0)),
            request_timeout=float(env.get("COLLECTOR_REQUEST_TIMEOUT", 30.0)),
            raw_data_dir=Path(env.get("COLLECTOR_RAW_DATA_DIR", "data/raw")),
            log_dir=Path(env.get("COLLECTOR_LOG_DIR", "logs")),
            log_level=env.get("COLLECTOR_LOG_LEVEL", "INFO").upper(),
            headless=env.get("COLLECTOR_HEADLESS", "true").strip().lower() not in ("0", "false", "no"),
            slow_mo_ms=int(env.get("COLLECTOR_SLOW_MO_MS", 0)),
            hold_seconds=float(env.get("COLLECTOR_HOLD_SECONDS", 0)),
            contact_email=env.get("COLLECTOR_CONTACT_EMAIL", ""),
            alert_webhook_url=env.get("COLLECTOR_ALERT_WEBHOOK_URL", ""),
            storage_backend=env.get("COLLECTOR_STORAGE", "local").lower(),
            s3_bucket=env.get("COLLECTOR_S3_BUCKET", ""),
            s3_prefix=env.get("COLLECTOR_S3_PREFIX", "raw/"),
        )


_KNOWN_KEYS = {"source_id", "url", "type", "enabled", "tos_allows_scraping", "tos_note"}


def _parse_source(raw: dict, index: int) -> Source:
    where = f"sources[{index}]"
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}: must be an object")
    for key in ("source_id", "url", "type"):
        if not raw.get(key) or not isinstance(raw[key], str):
            raise ConfigError(f"{where}: missing or invalid '{key}'")
    if not SOURCE_ID_PATTERN.match(raw["source_id"]):
        raise ConfigError(f"{where}: source_id may only contain letters, digits, '_', '-', '.'")
    if not raw["url"].lower().startswith(("http://", "https://")):
        raise ConfigError(f"{where}: url must start with http:// or https://")
    # Anything not a known key is a collector option; an explicit "options" object is merged in.
    options = {k: v for k, v in raw.items() if k not in _KNOWN_KEYS and k != "options"}
    options.update(raw.get("options") or {})
    return Source(
        source_id=raw["source_id"],
        url=raw["url"],
        type=raw["type"].lower(),
        enabled=bool(raw.get("enabled", True)),
        tos_allows_scraping=bool(raw.get("tos_allows_scraping", True)),
        tos_note=str(raw.get("tos_note", "")),
        options=options,
    )


def load_sources(path: Union[str, Path], enabled_only: bool = True) -> list[Source]:
    """Load sources.json. Disabled sources are dropped unless enabled_only=False."""
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))  # tolerate a Windows BOM
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
        raise ConfigError(f"{path}: top level must be an object with a 'sources' list")

    sources = [_parse_source(item, i) for i, item in enumerate(data["sources"])]
    ids = [s.source_id for s in sources]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ConfigError(f"Duplicate source_id(s): {sorted(duplicates)}")
    return [s for s in sources if s.enabled] if enabled_only else sources
