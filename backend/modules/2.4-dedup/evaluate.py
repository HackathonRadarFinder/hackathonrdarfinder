"""Evaluate dedup.py against labeled pairs.

Run:  python evaluate.py labeled_pairs_20.csv
"""
import csv
import sys
from pathlib import Path
from dedup import compare, map_record

REQUIRED = [
    "registration_link_1", "title_1", "organizer_1", "start_date_1", "location_1",
    "registration_link_2", "title_2", "organizer_2", "start_date_2", "location_2",
    "is_duplicate",
]
TRUE_VALUES = ("1", "true", "yes")
FALSE_VALUES = ("0", "false", "no")


def build_event(row, n):
    return {
        "registration_link": row.get(f"registration_link_{n}", ""),
        "title": row.get(f"title_{n}", ""),
        "organizer": row.get(f"organizer_{n}", ""),
        "start_date": row.get(f"start_date_{n}", ""),
        "location": row.get(f"location_{n}", ""),
    }


def evaluate_pairs(csv_file):
    path = Path(csv_file)
    if not path.exists():
        sys.exit(f"Error: CSV file not found: {csv_file}")

    tp = tn = fp = fn = uncertain = invalid = 0

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            sys.exit("Error: CSV file is empty or has no header.")
        missing = [c for c in REQUIRED if c not in reader.fieldnames]
        if missing:
            sys.exit("Error: Missing CSV columns: " + ", ".join(missing))

        for row_number, row in enumerate(reader, start=2):
            actual = (row.get("is_duplicate") or "").strip().lower()
            if actual not in TRUE_VALUES + FALSE_VALUES:
                invalid += 1
                print(f"Invalid label: CSV row {row_number}")
                continue

            actual_dup = actual in TRUE_VALUES
            e1, e2 = build_event(row, 1), build_event(row, 2)
            label, reason, score = compare(map_record(e1, 0), map_record(e2, 1))
            predicted_dup = label == "duplicate"

            if label == "uncertain":
                uncertain += 1

            if actual_dup and predicted_dup:
                tp += 1
            elif not actual_dup and not predicted_dup:
                tn += 1
            else:
                kind = "FALSE POSITIVE" if predicted_dup else "FALSE NEGATIVE"
                if predicted_dup:
                    fp += 1
                else:
                    fn += 1
                print(f"{kind} (row {row_number}, predicted={label}, reason={reason})")
                print(f"   A: {e1['title']} | {e1['start_date']} | {e1['location']}")
                print(f"   B: {e2['title']} | {e2['start_date']} | {e2['location']}")

    total = tp + tn + fp + fn
    if total == 0:
        sys.exit("No valid rows evaluated.")

    accuracy = (tp + tn) / total * 100
    precision = tp / (tp + fp) * 100 if (tp + fp) else 0.0
    recall = tp / (tp + fn) * 100 if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    print("\n===== DEDUPLICATION EVALUATION =====")
    print(f"Evaluated pairs : {total}   (invalid skipped: {invalid})")
    print(f"TP={tp}  TN={tn}  FP={fp}  FN={fn}")
    print(f"Uncertain pairs : {uncertain}  (counted as not-duplicate)")
    print(f"Accuracy        : {accuracy:.2f}%")
    print(f"Precision       : {precision:.2f}%")
    print(f"Recall          : {recall:.2f}%")
    print(f"F1 score        : {f1:.2f}%")


if __name__ == "__main__":
    evaluate_pairs(sys.argv[1] if len(sys.argv) > 1 else "labeled_pairs_20.csv")
