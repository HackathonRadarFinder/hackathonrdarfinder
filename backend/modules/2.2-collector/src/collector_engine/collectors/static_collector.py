"""Static collector: plain HTML/JSON fetch through Scrapy (cheap, no browser)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from ..models import FetchResponse, Source, TemporaryFetchError, PermanentFetchError
from .base_collector import BaseCollector, check_not_challenge, check_status

_RUNNER = Path(__file__).with_name("_scrapy_runner.py")


class StaticCollector(BaseCollector):
    collector_type = "static"

    def fetch(self, source: Source) -> FetchResponse:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "result.json"
            args = {
                "url": source.url,
                "out_path": str(out_path),
                "user_agent": self.settings.user_agent,
                "headers": {
                    k: v for k, v in self.settings.request_headers().items() if k != "User-Agent"
                },
                "delay": self.settings.min_delay,
                "timeout": self.settings.request_timeout,
            }
            try:
                proc = subprocess.run(
                    [sys.executable, str(_RUNNER), json.dumps(args)],
                    capture_output=True,
                    text=True,
                    timeout=self.settings.request_timeout * 3 + 30,
                )
            except subprocess.TimeoutExpired as exc:
                raise TemporaryFetchError(f"Scrapy run timed out for {source.url}") from exc
            if not out_path.exists():
                tail = (proc.stderr or "").strip()[-400:]
                raise TemporaryFetchError(f"Scrapy produced no result (exit {proc.returncode}): {tail}")
            data = json.loads(out_path.read_text(encoding="utf-8"))

        if "error" in data:
            if data["error_type"] == "IgnoreRequest":  # Scrapy's own robots.txt layer said no
                raise PermanentFetchError(f"Request ignored by Scrapy (robots.txt?): {data['error']}")
            raise TemporaryFetchError(f"{data['error_type']}: {data['error']}")

        check_status(data["http_status"], source.url)
        check_not_challenge(data["content"], source.url)
        return FetchResponse(
            url=source.url,
            http_status=data["http_status"],
            content=data["content"],
            content_type=data["content_type"],
            final_url=data["final_url"],
        )
