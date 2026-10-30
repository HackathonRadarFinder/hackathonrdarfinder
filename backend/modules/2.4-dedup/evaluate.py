
import csv
from pathlib import Path
from dedup import are_duplicates

REQUIRED_COLUMNS = [
    "registration_link_1", "title_1", "organizer_1", "start_date_1", "location_1",
    "registration_link_2", "title_2", "organizer_2", "start_date_2", "location_2",
    "is_duplicate",
]
FIELDS = ["registration_link", "title", "organizer", "start_date", "location"]


def evaluate_pairs(csv_file):
    """Run are_duplicates() over labeled pairs."""
    path = Path(csv_file)
    if not path.exists():
        print(f"Error: CSV file not found: {csv_file}")
        return 0, 0, []

    total = 0
    correct = 0
    false_positives = 0
    false_negatives = 0
    invalid_rows = 0
    mistakes = []

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            print("Error: CSV file is empty or has no header.")
            return 0, 0, []

        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            print("Error: Missing CSV columns:")
            for column in missing:
                print(f"- {column}")
            return 0, 0, []

        for row_number, row in enumerate(reader, start=2):
            actual = (row.get("is_duplicate") or "").strip().lower()

            if actual not in ("1", "0", "true", "false", "yes", "no"):
                invalid_rows += 1
                print(f"Invalid label: CSV row {row_number}")
                continue

            event1 = {f: row.get(f"{f}_1", "") for f in FIELDS}
            event2 = {f: row.get(f"{f}_2", "") for f in FIELDS}

            actual_duplicate = actual in ("1", "true", "yes")
            predicted_duplicate = are_duplicates(event1, event2)

            total += 1

            if actual_duplicate == predicted_duplicate:
                correct += 1
            else:
                mistakes.append((
                    row_number,
                    event1["title"],
                    event2["title"],
                    actual_duplicate,
                    predicted_duplicate
                ))

                if predicted_duplicate:
                    false_positives += 1
                    print(f"False positive: CSV row {row_number}")
                else:
                    false_negatives += 1
                    print(f"False negative: CSV row {row_number}")

    accuracy = correct / total * 100 if total else 0

    print("\n===== DEDUPLICATION EVALUATION =====")
    print(f"Evaluated pairs: {total}")
    print(f"Correct predictions: {correct}")
    print(f"Incorrect predictions: {total - correct}")
    print(f"False positives: {false_positives}")
    print(f"False negatives: {false_negatives}")
    print(f"Invalid rows skipped: {invalid_rows}")
    print(f"Accuracy: {accuracy:.2f}%")

    for line_no, t1, t2, actual, predicted in mistakes:
        print(
            f"MISS (CSV line {line_no}): "
            f"'{t1}' vs '{t2}' -> expected {actual}, got {predicted}"
        )

    return total, correct, mistakes


if __name__ == "__main__":
    evaluate_pairs("labeled_pairs_20.csv")
