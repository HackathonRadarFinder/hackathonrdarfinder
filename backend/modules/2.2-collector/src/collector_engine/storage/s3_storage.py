"""S3 implementation of RawStorage (same layout and records as LocalRawStorage).

Keys:  <prefix><source_id>/<stamp>.html|.json   and   <prefix><source_id>/<stamp>.meta.json
Credentials/region come from the standard AWS mechanisms (env vars, ~/.aws, IAM role).
The returned location is the .meta.json key relative to the prefix.
"""
from __future__ import annotations

import json
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


class S3RawStorage(RawStorage):
    def __init__(self, bucket: str, prefix: str = "raw/", client: Any = None):
        if not bucket:
            raise ValueError("S3 bucket name is required (COLLECTOR_S3_BUCKET)")
        self.bucket = bucket
        self.prefix = prefix if prefix.endswith("/") or not prefix else prefix + "/"
        if client is None:
            import boto3  # imported lazily: only needed when S3 is actually used

            client = boto3.client("s3")
        self.client = client

    def _exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:  # missing key (404) -> not found; real errors surface on put_object
            return False

    def save(self, result: CollectionResult) -> str:
        require_storable(result)
        base = stamp = file_stamp(result)
        folder = f"{self.prefix}{result.source_id}"
        n = 1
        while self._exists(f"{folder}/{stamp}.meta.json"):
            n += 1
            stamp = f"{base}-{n}"

        raw_name = f"{stamp}.{raw_extension(result)}"
        meta_key = f"{folder}/{stamp}.meta.json"
        self.client.put_object(
            Bucket=self.bucket,
            Key=f"{folder}/{raw_name}",
            Body=result.raw_content.encode("utf-8"),
            ContentType=result.content_type or "text/html",
        )
        # metadata is written last: a .meta.json only exists once its raw file is safely stored
        self.client.put_object(
            Bucket=self.bucket,
            Key=meta_key,
            Body=json.dumps(build_metadata(result, raw_name), indent=2, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )
        location = meta_key[len(self.prefix):]
        result.storage_location = location
        return location

    def load(self, location: str) -> dict[str, Any]:
        meta_key = f"{self.prefix}{location}"
        meta = json.loads(self.client.get_object(Bucket=self.bucket, Key=meta_key)["Body"].read())
        raw_key = meta_key.rsplit("/", 1)[0] + "/" + meta["raw_file"]
        raw = self.client.get_object(Bucket=self.bucket, Key=raw_key)["Body"].read().decode("utf-8")
        return handoff_record(meta, raw)

    def list_locations(self, source_id: str | None = None) -> list[str]:
        prefix = f"{self.prefix}{source_id}/" if source_id else self.prefix
        keys: list[str] = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            keys += [o["Key"] for o in page.get("Contents", []) if o["Key"].endswith(".meta.json")]
        return sorted(k[len(self.prefix):] for k in keys)
