"""S3 implementation of RawStorage (same layout and records as LocalRawStorage).

Keys:  <prefix><source_id>/<stamp>.html|.json   and   <prefix><source_id>/<stamp>.meta.json
Credentials/region come from the standard AWS mechanisms (env vars, ~/.aws, IAM role).
The returned location is the .meta.json key relative to the prefix.
"""
from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from ..models import CollectionResult, validate_source_id
from .base import (
    RawStorage,
    build_metadata,
    file_stamp,
    handoff_record,
    raw_extension,
    require_storable,
    validate_location,
)


class S3RawStorage(RawStorage):
    def __init__(self, bucket: str, prefix: str = "raw/", client: Any = None):
        if not bucket:
            raise ValueError("S3 bucket name is required (COLLECTOR_S3_BUCKET)")
        self.bucket = bucket
        self.prefix = validate_location(prefix.rstrip("/")) + "/" if prefix else ""
        if client is None:
            import boto3  # imported lazily: only needed when S3 is actually used

            client = boto3.client("s3")
        self.client = client

    def _exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except KeyError:  # supports the injected in-memory test client
            return False
        except Exception as exc:
            code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            if code in ("404", "NoSuchKey", "NotFound"):
                return False
            raise

    def save(self, result: CollectionResult) -> str:
        require_storable(result)
        stamp = f"{file_stamp(result)}-{uuid4().hex}"
        folder = f"{self.prefix}{result.source_id}"

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
        validate_location(location)
        meta_key = f"{self.prefix}{location}"
        meta = json.loads(self.client.get_object(Bucket=self.bucket, Key=meta_key)["Body"].read())
        raw_file = validate_location(meta["raw_file"])
        if "/" in raw_file:
            raise ValueError("Raw filename must be a basename")
        raw_key = meta_key.rsplit("/", 1)[0] + "/" + raw_file
        raw = self.client.get_object(Bucket=self.bucket, Key=raw_key)["Body"].read().decode("utf-8")
        return handoff_record(meta, raw)

    def list_locations(self, source_id: str | None = None) -> list[str]:
        if source_id is not None:
            validate_source_id(source_id)
        prefix = f"{self.prefix}{source_id}/" if source_id else self.prefix
        keys: list[str] = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            keys += [o["Key"] for o in page.get("Contents", []) if o["Key"].endswith(".meta.json")]
        return sorted(k[len(self.prefix):] for k in keys)
