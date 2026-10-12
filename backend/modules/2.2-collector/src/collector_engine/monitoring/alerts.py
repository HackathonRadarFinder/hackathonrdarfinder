"""Alert when a source blocks us (403/429/CAPTCHA). Lightweight: log + alerts file + optional webhook."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from ..models import CollectionResult
from .logger import get_logger

log = get_logger("alert")


class Alerter:
    def __init__(
        self,
        log_dir: Path | str | None = None,
        webhook_url: str = "",
        session: Optional[requests.Session] = None,
    ):
        self.log_dir = Path(log_dir) if log_dir else None
        self.webhook_url = webhook_url
        self.session = session or requests.Session()

    def blocked(self, result: CollectionResult) -> None:
        """Raise an alert for a blocked source. Never raises."""
        event = {
            "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "type": "blocked",
            "source_id": result.source_id,
            "url": result.url,
            "collector": result.collector_type,
            "reason": result.error,
        }
        message = f"ALERT blocked source_id={event['source_id']} url={event['url']} reason={event['reason']}"
        log.critical(message)
        if self.log_dir:
            try:
                self.log_dir.mkdir(parents=True, exist_ok=True)
                with open(self.log_dir / "alerts.log", "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(event) + "\n")
            except OSError as exc:
                log.error("could not write alerts.log: %s", exc)
        if self.webhook_url:
            try:
                self.session.post(self.webhook_url, json={"text": message}, timeout=10)
            except requests.RequestException as exc:
                log.error("alert webhook failed: %s", exc)
