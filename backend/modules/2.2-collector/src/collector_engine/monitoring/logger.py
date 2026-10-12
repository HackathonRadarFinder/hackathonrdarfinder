"""Lightweight logging: stdlib logging to console + a rotating file."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from ..models import CollectionResult

LOGGER_NAME = "collector"
_FORMAT = "%(asctime)s %(levelname)-7s %(message)s"


def get_logger(name: str = "") -> logging.Logger:
    return logging.getLogger(f"{LOGGER_NAME}.{name}" if name else LOGGER_NAME)


def setup_logging(log_dir: Path | str | None = None, level: str = "INFO") -> logging.Logger:
    """Configure the 'collector' logger. Safe to call more than once."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    formatter = logging.Formatter(_FORMAT)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            Path(log_dir) / "collector.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


def job_summary(result: CollectionResult) -> str:
    """One key=value line per finished job: the main monitoring record."""
    robots = {True: "allowed", False: "disallowed", None: "not_checked"}[result.robots_allowed]
    return (
        f"JOB_END source_id={result.source_id} url={result.url} collector={result.collector_type} "
        f"status={result.status} start={result.started_at} end={result.ended_at} "
        f"robots={robots} http_status={result.http_status} content_size={result.content_size} "
        f"items={result.item_count if result.item_count is not None else '-'} "
        f"attempts={result.attempts} reason={result.robots_reason or result.error or '-'}"
    )
