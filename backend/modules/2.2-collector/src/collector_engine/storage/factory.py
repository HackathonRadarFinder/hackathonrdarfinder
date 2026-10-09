"""Chooses the storage backend from settings (COLLECTOR_STORAGE=local|s3)."""
from __future__ import annotations

from ..config.loader import Settings
from .base import RawStorage
from .local_storage import LocalRawStorage


def create_storage(settings: Settings) -> RawStorage:
    if settings.storage_backend == "local":
        return LocalRawStorage(settings.raw_data_dir)
    if settings.storage_backend == "s3":
        from .s3_storage import S3RawStorage

        return S3RawStorage(settings.s3_bucket, settings.s3_prefix)
    raise ValueError(f"Unknown COLLECTOR_STORAGE '{settings.storage_backend}' (use 'local' or 's3')")
