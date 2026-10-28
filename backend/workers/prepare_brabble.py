"""Offline Brabble audit and review-queue export. Never writes a database."""
import argparse
import json
from pathlib import Path
from app.services.brabble_adapter import prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("radar_collector/output/brabble-live"))
    parser.add_argument("--out", type=Path, default=Path("radar_collector/output/brabble-review"))
    args = parser.parse_args()
    report = prepare(args.input, args.out)
    print(json.dumps({key: value for key, value in report.items()
                      if key not in {"schema_errors", "rejected_records", "duplicate_urls"}}, indent=2))


if __name__ == "__main__":
    main()
