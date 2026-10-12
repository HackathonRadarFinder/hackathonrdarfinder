"""CLI entry point:  python run.py [--config config/sources.json] [--source ID ...]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from .config.loader import ConfigError, Settings, load_sources
from .manager import CollectorManager
from .monitoring.logger import get_logger, setup_logging
from .storage.factory import create_storage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Module 2.2 - compliant collector engine")
    parser.add_argument("--config", default="config/sources.json", help="path to sources.json")
    parser.add_argument("--source", action="append", help="only run this source_id (repeatable)")
    args = parser.parse_args(argv)

    load_dotenv()
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    setup_logging(settings.log_dir, settings.log_level)
    log = get_logger("main")

    try:
        sources = load_sources(Path(args.config))
    except ConfigError as exc:
        log.error("Config error: %s", exc)
        return 2
    if args.source:
        sources = [s for s in sources if s.source_id in args.source]
        if not sources:
            log.error("No enabled source matches %s", args.source)
            return 2

    try:
        storage = create_storage(settings)
    except ValueError as exc:
        log.error("Storage config error: %s", exc)
        return 2
    manager = CollectorManager(settings, storage)
    results = manager.run(sources)
    # Non-zero only for real failures; skipped/blocked are expected compliant outcomes.
    return 1 if any(r.status == "failed" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
