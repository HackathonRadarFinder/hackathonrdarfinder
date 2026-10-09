"""Local filesystem implementation of RawStorage.

Layout:  <root>/<source_id>/<YYYYMMDDTHHMMSSZ>.html|.json   <- untouched raw content
                                              .meta.json  <- metadata (no raw_content)
The location string returned by save() is the path of the .meta.json file (relative to root).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import CollectionResult
from .base import (
    RawStorage,
    build_metadata,
    file_stamp,
    handoff_record,
    raw_extension,
    require_storable,
)


class LocalRawStorage(RawStorage):
    def __init__(self, root: Path | str):
        self.root = Path(root)

    def save(self, result: CollectionResult) -> str:
        require_storable(result)
        base = stamp = file_stamp(result)
        folder = self.root / result.source_id
        folder.mkdir(parents=True, exist_ok=True)
        n = 1
        while (folder / f"{stamp}.meta.json").exists():  # two fetches in the same second
            n += 1
            stamp = f"{base}-{n}"

        raw_path = folder / f"{stamp}.{raw_extension(result)}"
        meta_path = folder / f"{stamp}.meta.json"
        raw_path.write_text(result.raw_content, encoding="utf-8", newline="")
        meta_path.write_text(
            json.dumps(build_metadata(result, raw_path.name), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        location = meta_path.relative_to(self.root).as_posix()
        result.storage_location = location
        return location

    def load(self, location: str) -> dict[str, Any]:
        meta_path = self.root / location
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        raw = (meta_path.parent / meta["raw_file"]).read_text(encoding="utf-8")
        return handoff_record(meta, raw)

    def list_locations(self, source_id: str | None = None) -> list[str]:
        base = self.root / source_id if source_id else self.root
        if not base.exists():
            return []
        return sorted(p.relative_to(self.root).as_posix() for p in base.rglob("*.meta.json"))
