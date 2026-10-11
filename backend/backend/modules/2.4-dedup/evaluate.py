"""
Tests dedup.py rules against your manually labeled pairs.
Run: python evaluate.py labeled_pairs.csv
"""
import csv
import sys

from dedup import compare


def row_to_events(r):
    a = {"title": r["title_a"], "organizer": r["organizer_a"], "start_date": r["date_a"],
         "location": r["location_a"], "registration_link": r["link_a"]}
    b = {"title": r["title_b"], "organizer": r["organizer_b"], "start_date": r["date_b"],
         "location": r["location_b"], "registration_link": r["link_b"]}
    return a, b


def main(path):
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8")))
    correct, total = 0, 0
    print(f"{'ID':<4}{'YOUR LABEL':<16}{'PREDICTED':<16}{'OK?':<6}REASON")
    print("-" * 80)
    for r in rows:
        a, b = row_to_events(r)
        predicted, reason, score = compare(a, b)
        actual = r["label"].strip().lower().replace("-", "_").replace(" ", "_")
        if actual == "non_duplicate":
            actual = "not_duplicate"
        if actual == "uncertain":
            ok = "skip"
        else:
            total += 1
            ok = "yes" if predicted == actual else "NO"
            correct += predicted == actual
        print(f"{r['pair_id']:<4}{actual:<16}{predicted:<16}{ok:<6}{reason}")
    if total:
        print(f"\nAccuracy (excluding Uncertain): {correct}/{total} = {100 * correct / total:.0f}%")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "labeled_pairs.csv")
