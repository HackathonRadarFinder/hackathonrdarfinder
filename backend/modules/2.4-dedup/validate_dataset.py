"""Offline quality audit for a row-level Unstop CSV/JSON export.

This validates local structure and internal consistency only. It does not make
HTTP requests or claim that URLs are live or that scraping is policy-compliant.
Usage: python validate_dataset.py path/to/unstop_export.json [--out-dir audit_output]
"""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

from dedup import load, normalize_link

REQUIRED = ("title", "organizer", "start_date", "registration_link", "end_date", "registration_deadline", "mode")
URL_FIELDS = ("source_url", "registration_link")


def structurally_valid_url(value):
    if not value:
        return False
    p = urlparse(value if "://" in value else "https://" + value)
    return p.scheme in ("http", "https") and bool(p.hostname) and "." in p.hostname


def audit(path):
    records = load(str(path))
    missing = Counter()
    invalid_dates = Counter()
    invalid_urls = Counter()
    exact_links = defaultdict(list)
    source_counts = Counter()
    mode_counts = Counter()
    status_counts = Counter()
    prize_present = 0
    start_date_present = end_date_present = deadline_present = 0

    for i, r in enumerate(records, 1):
        for f in REQUIRED:
            if not (r.get(f) or "").strip():
                missing[f] += 1
        for f in URL_FIELDS:
            if r.get(f) and not structurally_valid_url(r[f]):
                invalid_urls[f] += 1
        link = normalize_link(r.get("registration_link", ""))
        if link:
            exact_links[link].append({"row_number": i, "source_id": r.get("source_id", ""), "title": r.get("title", ""), "registration_link": r.get("registration_link", "")})
        source_counts[r.get("source") or "unknown"] += 1
        mode_counts[r.get("mode") or "(missing)"] += 1
        status_counts[r.get("status") or "(missing)"] += 1
        prize_present += bool((r.get("prize") or "").strip())
        start_date_present += bool(r.get("start_date"))
        end_date_present += bool(r.get("end_date"))
        deadline_present += bool(r.get("registration_deadline"))

    duplicate_groups = [items for items in exact_links.values() if len(items) > 1]
    duplicate_rows = sum(len(g) for g in duplicate_groups)
    report = {
        "input_file": str(path),
        "total_records": len(records),
        "required_field_missing_counts": dict(missing),
        "records_with_prize": prize_present,
        "records_with_start_date": start_date_present,
        "records_with_end_date": end_date_present,
        "records_with_registration_deadline": deadline_present,
        "url_structural_issue_counts": dict(invalid_urls),
        "exact_normalized_registration_link_duplicate_groups": len(duplicate_groups),
        "records_in_exact_link_duplicate_groups": duplicate_rows,
        "source_counts": dict(source_counts),
        "mode_counts": dict(mode_counts),
        "status_counts": dict(status_counts),
        "limitations": [
            "URL checks are structural only; no live HTTP checks were performed.",
            "Exact-link duplicate groups are not the same as all fuzzy/entity duplicates.",
            "Robots.txt and terms compliance are not established by this data audit."
        ]
    }
    return report, duplicate_groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_file", help="Row-level CSV or JSON export")
    parser.add_argument("--out-dir", default="unstop_audit_output", help="Directory for JSON report and duplicate CSV")
    args = parser.parse_args()
    report, groups = audit(args.input_file)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "dataset_audit_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    with (out / "exact_link_duplicate_groups.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["duplicate_group", "row_number", "source_id", "title", "registration_link"])
        writer.writeheader()
        for group_no, group in enumerate(groups, 1):
            for item in group:
                writer.writerow({"duplicate_group": group_no, **item})
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nSaved: {out / 'dataset_audit_report.json'}")
    print(f"Saved: {out / 'exact_link_duplicate_groups.csv'}")


if __name__ == "__main__":
    main()
