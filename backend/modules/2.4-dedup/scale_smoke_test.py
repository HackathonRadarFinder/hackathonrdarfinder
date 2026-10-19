"""Reproducible synthetic scale smoke test; does not use real Unstop records."""
import json
import time
from datetime import date, timedelta
from pathlib import Path

from dedup import cluster, map_record, merge_group


def build_records(unique_count=6766, duplicate_count=30):
    base = date(2010, 1, 1)
    rows = []
    for i in range(unique_count):
        start = base + timedelta(days=(i // 2) % 6500)
        rows.append(map_record({
            "source": "unstop" if i % 2 == 0 else "devfolio",
            "source_id": f"scale_{i}",
            "source_url": f"https://example.test/event/{i}",
            "title": f"Event Category{i % 97} Unique{i}",
            "organizer": f"Org{i}",
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=1)).isoformat(),
            "registration_deadline": (start - timedelta(days=2)).isoformat(),
            "location": f"City{i % 25}",
            "mode": "Online" if i % 3 else "Offline",
            "status": "Open" if i % 5 else "Closed",
            "registration_link": f"https://example.test/register/{i}",
            "description": f"Synthetic record {i}",
            "prize": str((i % 20) * 1000),
            "tags": ["synthetic", "scale-test"],
        }, i))
    for k in range(duplicate_count):
        clone = rows[k * 2].copy()
        clone["source"] = "devfolio"
        clone["source_id"] = f"scale_duplicate_{k}"
        clone["source_url"] = f"https://devfolio.test/event/{k}"
        rows.append(clone)
    return rows


def main():
    rows = build_records()
    started = time.perf_counter()
    groups, uncertain = cluster(rows)
    elapsed = time.perf_counter() - started
    canonical = [merge_group(group, 101 + i) for i, group in enumerate(groups)]
    report = {
        "test_type": "synthetic scale smoke test; not real-world accuracy evidence",
        "input_records": len(rows),
        "expected_unique_records": 6766,
        "canonical_records": len(canonical),
        "merged_duplicates": len(rows) - len(canonical),
        "expected_exact_link_duplicates": 30,
        "uncertain_pairs": len(uncertain),
        "elapsed_seconds": round(elapsed, 3),
        "tags_preserved": all("tags" in event for event in canonical),
        "source_name_preserved": all("source_name" in event for event in canonical),
    }
    Path("scale_smoke_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["canonical_records"] != 6766 or report["merged_duplicates"] != 30:
        raise SystemExit("Scale smoke test failed expected count assertions")


if __name__ == "__main__":
    main()
