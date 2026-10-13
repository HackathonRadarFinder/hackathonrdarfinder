
import csv
from dedup import are_duplicates


def evaluate_pairs(csv_file):
    total = 0
    correct = 0

    with open(csv_file, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
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

            actual = row.get("is_duplicate", "").strip().lower()
            if actual not in ("1", "0", "true", "false", "yes", "no"):
                continue

            actual_duplicate = actual in ("1", "true", "yes")
            predicted_duplicate = are_duplicates(event1, event2)

            total += 1
            if actual_duplicate == predicted_duplicate:
                correct += 1

    accuracy = (correct / total * 100) if total else 0

    print(f"Evaluated pairs: {total}")
    print(f"Correct predictions: {correct}")
    print(f"Accuracy: {accuracy:.2f}%")


if __name__ == "__main__":
    evaluate_pairs("labeled_pairs_20.csv")
