
import json
from pathlib import Path


def load_events(file_path):
    """Load events from a JSON file."""
    path = Path(file_path)

    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_events(events, file_path):
    """Save events to a JSON file."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(events, file, indent=4, ensure_ascii=False)


def merge_events(existing, new_event):
    """Merge source information into an existing canonical event."""
    merged = existing.copy()

    source_ids = set(existing.get("source_ids", []))
    source_ids.update(new_event.get("source_ids", []))

    if new_event.get("source_id"):
        source_ids.add(new_event["source_id"])

    merged["source_ids"] = sorted(source_ids)

    sources = set(existing.get("sources", []))
    sources.update(new_event.get("sources", []))

    if new_event.get("source"):
        sources.add(new_event["source"])

    merged["sources"] = sorted(sources)

    # Fill missing fields without overwriting existing values.
    for key, value in new_event.items():
        if key not in merged or merged[key] in ("", None, []):
            merged[key] = value

    return merged


def update_master_db(master_events, new_event, is_duplicate):
    """Merge duplicates or append a new event."""
    if is_duplicate:
        for index, event in enumerate(master_events):
            master_events[index] = merge_events(event, new_event)
            return master_events

    master_events.append(new_event)
    return master_events
