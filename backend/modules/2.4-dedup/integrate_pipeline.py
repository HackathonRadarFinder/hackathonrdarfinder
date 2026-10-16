"""Integration adapter for Module 2.3 JSON outputs -> Module 2.4.

Expected input directory (default: module_2_3/output):
  valid_events.json (required; invalid events must never be passed here)
  expired_events.json (optional; used only with --include-expired)

Outputs master_events.json, uncertain_pairs.json, and a SQLite master database.
"""
import argparse
import json
from pathlib import Path

from dedup import map_record, cluster, merge_group
from master_db import save_master


def read_events(path):
    """Read a JSON list, or a wrapper object containing an events/valid/expired list."""
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        for key in ("events", "valid", "expired"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON list of event objects")
    if any(not isinstance(item, dict) for item in data):
        raise ValueError(f"{path} must contain only JSON event objects")
    return data


def run_pipeline(input_dir, output_dir, db_path, include_expired=False):
    input_dir = Path(input_dir)
    raw_events = read_events(input_dir / "valid_events.json")
    if include_expired:
        raw_events += read_events(input_dir / "expired_events.json")

    events = [map_record(event, i) for i, event in enumerate(raw_events)]
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not events:
        return {"input": 0, "canonical": 0, "duplicates_merged": 0,
                "uncertain": 0, "message": f"No events found in {input_dir / 'valid_events.json'}"}

    groups, uncertain = cluster(events)
    master = [merge_group(group, 101 + i) for i, group in enumerate(groups)]
    (output_dir / "master_events.json").write_text(
        json.dumps(master, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "uncertain_pairs.json").write_text(
        json.dumps(uncertain, indent=2, ensure_ascii=False), encoding="utf-8")
    stats = save_master(master, db_path=str(db_path))
    return {"input": len(events), "canonical": len(master),
            "duplicates_merged": len(events) - len(master),
            "uncertain": len(uncertain), "stats": stats,
            "master_json": str(output_dir / "master_events.json"),
            "review_json": str(output_dir / "uncertain_pairs.json"),
            "database": str(db_path)}


def main():
    parser = argparse.ArgumentParser(description="Run Module 2.4 on Module 2.3 canonical JSON outputs.")
    parser.add_argument("--input-dir", default="module_2_3/output")
    parser.add_argument("--include-expired", action="store_true")
    parser.add_argument("--db", default="master_events.db")
    parser.add_argument("--output-dir", default="module_2_4_output")
    args = parser.parse_args()
    result = run_pipeline(args.input_dir, args.output_dir, args.db, args.include_expired)
    if "message" in result:
        print(result["message"])
        return
    print(f"Input events: {result['input']}")
    print(f"Canonical events: {result['canonical']}")
    print(f"Duplicates merged: {result['duplicates_merged']}")
    print(f"Uncertain pairs: {result['uncertain']}")
    print(f"Master JSON: {result['master_json']}")
    print(f"Review JSON: {result['review_json']}")
    print(f"SQLite DB: {result['database']} (new={result['stats']['new']}, updated={result['stats']['updated']}, total={result['stats']['total']})")


if __name__ == "__main__":
    main()
