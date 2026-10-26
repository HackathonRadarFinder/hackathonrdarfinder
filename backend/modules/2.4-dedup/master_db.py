import json
from pathlib import Path
from dedup import are_duplicates


def load_events(file_path):
    """Load events from a JSON file."""
    path = Path(file_path)

    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        events = json.load(file)

    if not isinstance(events, list):
        raise ValueError("Master database must contain a JSON list.")

    return events


def save_events(events, file_path):
    """Save events to a JSON file."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(events, file, indent=4, ensure_ascii=False)


def merge_events(existing, new_event):
    """Merge event details and preserve source provenance."""
    merged = existing.copy()

    for key, value in new_event.items():
        if key in ("source_ids", "sources"):
            old_values = merged.get(key, [])
            old_values = old_values if isinstance(old_values, list) else [old_values]
            new_values = value if isinstance(value, list) else [value]

            combined = []
            for item in old_values + new_values:
                if item not in combined:
                    combined.append(item)

            merged[key] = combined

        elif key in ("source_id", "source") and value:
            target = "source_ids" if key == "source_id" else "sources"
            old_values = merged.get(target, [])
            old_values = old_values if isinstance(old_values, list) else [old_values]

            if value not in old_values:
                old_values.append(value)

            merged[target] = old_values

        elif key not in merged or merged[key] in ("", None, []):
            merged[key] = value

    return merged


def update_master_db(master_events, new_event):
    """Merge a duplicate event or append a new event."""
    for index, event in enumerate(master_events):
        if are_duplicates(event, new_event):
            master_events[index] = merge_events(event, new_event)
            return master_events

    master_events.append(new_event)
    return master_events
