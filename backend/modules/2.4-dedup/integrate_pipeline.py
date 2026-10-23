
"""Integration adapter for Module 2.3 outputs to Module 2.4 deduplication."""

import argparse
import json
from pathlib import Path

from dedup import map_record, cluster, merge_group
from master_db import save_master


def read_events(path):
    """Read a JSON list of event records."""
    path = Path(path)

    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        for key in ("events", "valid", "expired"):
            if isinstance(data.get(key), list):
                data = data[key]
                break

    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON list of events")

    if any(not isinstance(event, dict) for event in data):
        raise ValueError(f"{path} must contain only JSON event objects")

    return data


def run_pipeline(input_dir, output_dir, db_path, include_expired=False):
    """Run deduplication and save canonical events and review results."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    raw_events = read_events(input_dir / "valid_events.json")

    if include_expired:
        raw_events.extend(read_events(input_dir / "expired_events.json"))

    output_dir.mkdir(parents=True, exist_ok=True)

    if not raw_events:
        return {
            "input": 0,
            "canonical": 0,
            "duplicates_merged": 0,
            "uncertain": 0,
            "message": f"No events found in {input_dir / 'valid_events.json'}",
        }

    events = [
        map_record(event, index)
        for index, event in enumerate(raw_events)
    ]

    groups, uncertain = cluster(events)

    master = [
        merge_group(group, 101 + index)
        for index, group in enumerate(groups)
    ]

    master_path = output_dir / "master_events.json"
    review_path = output_dir / "uncertain_pairs.json"

    master_path.write_text(
        json.dumps(master, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    review_path.write_text(
        json.dumps(uncertain, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    stats = save_master(master, db_path=str(db_path))

    return {
        "input": len(events),
        "canonical": len(master),
        "duplicates_merged": len(events) - len(master),
        "uncertain": len(uncertain),
        "stats": stats,
        "master_json": str(master_path),
        "review_json": str(review_path),
        "database": str(db_path),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Integrate Module 2.3 event outputs with Module 2.4."
    )
    parser.add_argument(
        "--input-dir",
        default="module_2_3/output",
        help="Folder containing valid_events.json",
    )
    parser.add_argument(
        "--include-expired",
        action="store_true",
        help="Also process expired_events.json",
    )
    parser.add_argument(
        "--db",
        default="master_events.db",
        help="SQLite database path",
    )
    parser.add_argument(
        "--output-dir",
        default="module_2_4_output",
        help="Folder for output JSON files",
    )

    args = parser.parse_args()

    result = run_pipeline(
        args.input_dir,
        args.output_dir,
        args.db,
        args.include_expired,
    )

    if "message" in result:
        print(result["message"])
        return

    print(f"Input events: {result['input']}")
    print(f"Canonical events: {result['canonical']}")
    print(f"Duplicates merged: {result['duplicates_merged']}")
    print(f"Uncertain pairs: {result['uncertain']}")
    print(f"Master JSON: {result['master_json']}")
    print(f"Review JSON: {result['review_json']}")
    print(f"SQLite DB: {result['database']}")
    print(
        f"Database records: new={result['stats']['new']}, "
        f"updated={result['stats']['updated']}, "
        f"total={result['stats']['total']}"
    )


if __name__ == "__main__":
    main()
