"""Contained local raw storage; publish metadata atomically after its raw file."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..models import CollectionResult, validate_source_id
from .base import (RawStorage, build_metadata, file_stamp, handoff_record,
                   raw_extension, require_storable, validate_location)


class LocalRawStorage(RawStorage):
    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()

    def _within(self, location: str) -> Path:
        validate_location(location)
        target = (self.root / location).resolve()
        if not target.is_relative_to(self.root) or target == self.root:
            raise ValueError("Storage path escapes configured root")
        return target

    def save(self, result: CollectionResult) -> str:
        require_storable(result)
        folder = self._within(result.source_id)
        folder.mkdir(parents=True, exist_ok=True)
        stamp = f"{file_stamp(result)}-{uuid4().hex}"
        raw_name = f"{stamp}.{raw_extension(result)}"
        location = f"{result.source_id}/{stamp}.meta.json"
        raw_path = self._within(f"{result.source_id}/{raw_name}")
        meta_path = self._within(location)
        # Exclusive raw creation avoids overwriting any previous collection.
        with raw_path.open("x", encoding="utf-8", newline="") as stream:
            stream.write(result.raw_content)
        result.storage_location = location
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=folder,
                                         prefix=".metadata-", delete=False) as stream:
            json.dump(build_metadata(result, raw_name), stream, ensure_ascii=False, indent=2)
            temporary = stream.name
        os.replace(temporary, meta_path)
        return location

    def load(self, location: str) -> dict[str, Any]:
        meta_path = self._within(location)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        raw_name = validate_location(meta["raw_file"])
        if "/" in raw_name:
            raise ValueError("Raw filename must be a basename")
        raw_path = self._within(f"{Path(location).parent.as_posix()}/{raw_name}")
        return handoff_record(meta, raw_path.read_text(encoding="utf-8"))

    def list_locations(self, source_id: str | None = None) -> list[str]:
        base = self._within(validate_source_id(source_id)) if source_id is not None else self.root
        if not base.exists():
            return []
        locations = []
        for path in base.rglob("*.meta.json"):
            location = path.relative_to(self.root).as_posix()
            self._within(location)
            locations.append(location)
        return sorted(locations)
