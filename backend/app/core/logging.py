import logging
import sys

from app.core.config import settings


def configure_logging() -> None:
    """Configure application-wide logging."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for the given module."""
    return logging.getLogger(name)