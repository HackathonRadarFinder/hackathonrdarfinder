import csv
from pathlib import Path
from dedup import are_duplicates


def evaluate_pairs(csv_file):
    path = Path(csv_file)

    if not path.exists():
        print(f"Error: CSV file not found: {csv_file}")
        return

    total = 0
    correct = 0
    false_positives = 0
    false_negatives = 0
    invalid_rows = 0

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        required_columns = [
            "registration_link_1",
            "title_1",
            "organizer_1",
            "start_date_1",
            "location_1",
            "registration_link_2",
            "title_2",
            "organizer_2",
            "start_date_2",
            "location_2",
            "is_duplicate",
        ]

        if not reader.fieldnames:
            print("Error: CSV file is empty or has no header.")
            return

        missing_columns = [
            column for column in required_columns
            if column not in reader.fieldnames
        ]

        if missing_columns:
            print("Error: Missing CSV columns:")
            for column in missing_columns:
                print(f"- {column}")
            return

        for row_number, row in enumerate(reader, start=2):
            actual = (row.get("is_duplicate") or "").strip().lower()

            if actual not in ("1", "0", "true", "false", "yes", "no"):
                invalid_rows += 1
                print(f"Invalid label: CSV row {row_number}")
                continue

            event1 = {
                "registration_link": row.get("registration_link_1", ""),
                "title": row.get("title_1", ""),
                "organizer": row.get("organizer_1", ""),
                "start_date": row.get("start_date_1", ""),
                "location": row.get("location_1", ""),
            }

            event2 = {
                "registration_link": row.get("registration_link_2", ""),
                "title": row.get("title_2", ""),
                "organizer": row.get("organizer_2", ""),
                "start_date": row.get("start_date_2", ""),
                "location": row.get("location_2", ""),
            }

            actual_duplicate = actual in ("1", "true", "yes")
            predicted_duplicate = are_duplicates(event1, event2)

            total += 1

            if actual_duplicate == predicted_duplicate:
                correct += 1
            elif predicted_duplicate:
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


if __name__ == "__main__":
    evaluate_pairs("labeled_pairs_20.csv")