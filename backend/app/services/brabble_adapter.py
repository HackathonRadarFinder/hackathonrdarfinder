"""Offline Brabble API normalization. No network, database, or implicit approval."""
import hashlib
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from app.schemas.event import EventCreate
from radar_collector.radar_scraper import FIELDS, clean_url, source_for, save

ATTRIBUTION = "Data provided by Brabble.ai"
TERMS = "https://brabble.ai/docs"
VERIFICATIONS = {"organization", "url", "dates"}


class InvalidSourceURL(ValueError):
    pass


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Missing API acquisition/refresh timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("API timestamps require a timezone")
    return parsed.isoformat()


def text(value):
    result = re.sub(r"\s+", " ", str(value or "")).strip()
    # Repair only reversible UTF-8 decoded as a legacy encoding. Raw evidence stays intact.
    if any(marker in result for marker in ("â", "Ã", "Â")):
        for encoding in ("latin-1", "cp1252"):
            try:
                repaired = result.encode(encoding).decode("utf-8")
                if repaired != result:
                    result = repaired
                    break
            except (UnicodeError, LookupError):
                pass
    return "" if result.casefold() in {"see listing", "n/a", "unknown", "not provided"} else result


def record_hash(raw):
    return hashlib.sha256(json.dumps(raw, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_evidence(evidence):
    if not isinstance(evidence, dict) or evidence.get("provider") != "Brabble.ai":
        raise ValueError("Expected Brabble API evidence")
    raw = evidence.get("raw_record")
    if not isinstance(raw, dict) or evidence.get("api_record_sha256") != record_hash(raw):
        raise ValueError("API record checksum mismatch")
    if evidence.get("provider_id") != raw.get("id") or not text(raw.get("id")):
        raise ValueError("Provider identity mismatch")
    if (evidence.get("original_platform") != raw.get("platform")
            or evidence.get("original_url") != raw.get("url")):
        raise ValueError("Original platform evidence mismatch")
    share = urlsplit(evidence.get("provider_url", ""))
    if (share.scheme != "https" or share.hostname != "brabble.ai" or share.username
            or share.password or share.port or share.query or share.fragment
            or share.path != "/s/" + raw["id"]):
        raise ValueError("Invalid Brabble attribution URL")
    if evidence.get("method") != "brabble_api" or evidence.get("attribution") != ATTRIBUTION:
        raise ValueError("Missing truthful API attribution")
    timestamp(evidence.get("acquired_at"))
    timestamp(evidence.get("source_refreshed_at"))
    if raw.get("kind") not in {"competition", "contest"}:
        raise ValueError("Unknown API deadline kind")
    return evidence


def normalize(raw, exported):
    source = raw.get("platform")
    url = raw.get("url", "")
    try:
        valid_url = (isinstance(url, str) and not any(ord(c) <= 32 for c in url)
                     and not urlsplit(url).fragment and source in {"Unstop", "Devfolio"}
                     and source_for(url) == source)
    except ValueError:
        valid_url = False
    if not valid_url:
        raise InvalidSourceURL("Invalid platform/source URL")
    if raw.get("type") != "HACKATHON":
        raise ValueError("Expected a hackathon listing")
    deadline = timestamp(raw.get("deadline"))
    evidence = validate_evidence({
        "method": "brabble_api", "provider": "Brabble.ai", "provider_id": raw.get("id"),
        "provider_url": raw.get("shareUrl"), "attribution": ATTRIBUTION,
        "acquired_at": exported.get("acquired_at"),
        "source_refreshed_at": exported.get("source_refreshed_at"),
        "original_platform": source, "original_url": url,
        "api_record_sha256": record_hash(raw), "raw_record": raw,
        "verified_fields": [],
    })
    row = {key: "" for key in FIELDS}
    prize = raw.get("prize") or {}
    row.update(title=text(raw.get("title")), organization=text(raw.get("organiser")),
               source=source, url=clean_url(url), mode={"ONLINE": "Online", "OFFLINE": "Offline",
               "HYBRID": "Hybrid"}.get(raw.get("mode"), ""), location=text(raw.get("city")),
               prize=text(prize.get("label")), team_size=text(raw.get("team")),
               scraped_at=timestamp(exported.get("acquired_at")), review_status="needs_review",
               collection_mode="brabble_api", permission_reference=TERMS,
               date_precision="unknown", acquisition_evidence=evidence,
               description=f"{text(raw.get('title'))}. Listing supplied through the Brabble.ai API. "
                           "Prize labels and registration counts are provider-supplied and may be incomplete; "
                           "confirm details on the original platform.")
    if raw["kind"] == "competition":
        row["registration_deadline"] = deadline
    else:
        row["start_date"] = deadline
        row["date_precision"] = "exact"
    issues = []
    if not row["organization"]:
        issues.append("organization_missing")
    if not row["mode"]:
        issues.append("mode_unverified")
    if not row["start_date"]:
        issues.append("event_start_date_unknown")
    row["issues"] = "; ".join(issues + ["organization_url_dates_review_required"])
    return row


def prepare(directory: Path, output: Path):
    """Join original API rows to acquisition metadata; export review queue and audit."""
    exported = json.loads((directory / "hackathons.json").read_text(encoding="utf-8-sig"))
    with (directory / "hackathons.csv").open(encoding="utf-8-sig", newline="") as handle:
        csv_export = list(csv.DictReader(handle))
    # These exports contain scalar values only; PowerShell emits empty cells for nulls.
    csv_matches = len(csv_export) == len(exported) and all(
        all(str(item.get(key) if item.get(key) is not None else "") == value
            for key, value in csv_row.items()) for item, csv_row in zip(exported, csv_export))
    raw = [row for name in ("unstop.json", "devfolio.json")
           for row in json.loads((directory / name).read_text(encoding="utf-8-sig"))]
    by_id = defaultdict(list)
    for item in raw:
        by_id[item.get("id")].append(item)
    candidates, rejected, duplicates, schema_errors, invalid_urls = [], [], [], [], []
    seen = set()
    missing = Counter()
    titles = defaultdict(list)
    for index, item in enumerate(exported, 1):
        try:
            matches = by_id[item.get("provider_id")]
            if len(matches) != 1:
                raise ValueError("Missing or ambiguous raw provider record")
            original = matches[0]
            if item.get("source") != original.get("platform") or item.get("url") != original.get("url"):
                raise ValueError("Export/raw source identity mismatch")
            row = normalize(original, item)
            if row["url"] in seen:
                duplicates.append({"row": index, "url": row["url"]})
                continue
            seen.add(row["url"])
            for field in ("title", "organization", "start_date", "end_date", "registration_deadline",
                          "location", "mode", "prize"):
                if not row[field]:
                    missing[field] += 1
            try:
                EventCreate.model_validate({key: row.get(key) or None for key in (
                    "title", "organization", "start_date", "end_date", "registration_deadline",
                    "location", "mode", "prize", "description", "url", "source", "scraped_at")})
            except ValueError as exc:
                schema_errors.append({"provider_id": original["id"], "error": str(exc)})
            titles[re.sub(r"\W+", "", row["title"].casefold())].append(row["url"])
            candidates.append(row)
        except (ValueError, TypeError, KeyError) as exc:
            rejected.append({"row": index, "provider_id": item.get("provider_id"), "error": str(exc)})
            if isinstance(exc, InvalidSourceURL):
                invalid_urls.append({"row": index, "url": item.get("url"), "error": str(exc)})
    output.mkdir(parents=True, exist_ok=True)
    # JSON keeps structured evidence; CSV stores it as JSON text in one column.
    (output / "review_queue.json").write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_rows = [dict(row, acquisition_evidence=json.dumps(row["acquisition_evidence"], ensure_ascii=False))
                for row in candidates]
    save(csv_rows, output)
    # save()'s JSON is CSV-shaped; keep the structured review_queue.json as authoritative.
    report = {"input_records": len(exported), "raw_records": len(raw),
              "input_csv_json_match": csv_matches,
              "platforms": dict(Counter(row["source"] for row in candidates)),
              "schema_valid": len(candidates) - len(schema_errors), "schema_invalid": len(schema_errors),
              "rejected": len(rejected), "duplicates": len(duplicates),
              "pending_review": len(candidates), "approved": 0, "missing_fields": dict(missing),
              "rejected_records": rejected, "duplicate_urls": duplicates, "schema_errors": schema_errors,
              "invalid_url_count": len(invalid_urls), "invalid_urls": invalid_urls,
              "input_file_sha256": {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                                    for name in ("hackathons.csv", "hackathons.json", "unstop.json", "devfolio.json")},
              "possible_duplicate_titles": [urls for urls in titles.values() if len(urls) > 1],
              "database_writes": False, "acquisition": "Brabble.ai API; not direct platform scraping"}
    (output / "quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = ["# Brabble snapshot data quality", "",
               "Acquisition: supplied Brabble.ai API exports; no direct platform scraping.", "",
               f"Input: {len(exported)} records. CSV/JSON agree: {csv_matches}.",
               f"Schema valid: {report['schema_valid']}; schema invalid: {report['schema_invalid']}.",
               f"Rejected: {len(rejected)}; duplicate URLs: {len(duplicates)}; invalid URLs: {len(invalid_urls)}.",
               f"Pending human review: {len(candidates)}; approved: 0; database writes: 0.", "",
               "Schema validity is a technical check, not approval. Pending includes schema-valid rows.", "",
               "| Missing field after placeholder cleanup | Count |", "|---|---:|"]
    summary += [f"| {field} | {count} |" for field, count in missing.items()]
    summary += ["", "All current kinds are reported per row in retained raw evidence. Competition deadlines",
                "map to registration/application deadlines; contest deadlines map to starts. End dates are never inferred.",
                "", "Checksums cover supplied export files and canonical JSON API records, never HTML.",
                "Original HTTP envelopes were not supplied for this snapshot; their authenticity cannot be reconstructed."]
    (output / "quality_report.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return report
