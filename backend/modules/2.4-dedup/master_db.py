
import json
from pathlib import Path
from dedup import are_duplicates


def load_events(file_path):
    path = Path(file_path)

    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_events(events, file_path):
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(events, file, indent=4, ensure_ascii=False)


def merge_events(existing, new_event):
    merged = existing.copy()

    for key, value in new_event.items():
        if key in ("source_ids", "sources"):
            old = existing.get(key, [])
            old = old if isinstance(old, list) else [old]
            new = value if isinstance(value, list) else [value]
            merged[key] = sorted(set(old + new))

        elif key in ("source_id", "source") and value:
            target = "source_ids" if key == "source_id" else "sources"
            old = merged.get(target, [])
            old = old if isinstance(old, list) else [old]
            merged[target] = sorted(set(old + [value]))

        elif key not in merged or merged[key] in ("", None, []):
            merged[key] = value

    return merged


def update_master_db(master_events, new_event):
    for index, event in enumerate(master_events):
        if are_duplicates(event, new_event):
            master_events[index] = merge_events(event, new_event)
            return master_events

    master_events.append(new_event)
    return master_events
