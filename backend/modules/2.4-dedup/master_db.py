"""
Module 2.4 - Master database integration.

Two storage options live here:
  * save_master()        -> SQLite master database (canonical_events + event_source_links).
                            Used by `python dedup.py --db` and by test_module24.py.
  * update_master_db()   -> lightweight JSON-list helpers (load_events / save_events /
                            merge_events), kept so existing callers keep working.

save_master() never loses provenance: every (source, source_id) pair is stored in
event_source_links, and re-running with the same source_id updates the existing
canonical event instead of creating a duplicate.
"""
import json
import sqlite3
from datetime import date
from pathlib import Path

DEFAULT_DB_PATH = "master_events.db"

# column -> SQL definition used both for CREATE TABLE and for migrating older databases
EVENT_COLUMNS = {
    "organizer": "TEXT",
    "start_date": "TEXT",
    "end_date": "TEXT DEFAULT ''",
    "registration_deadline": "TEXT DEFAULT ''",
    "mode": "TEXT DEFAULT ''",
    "status": "TEXT DEFAULT ''",
    "location": "TEXT",
    "registration_link": "TEXT",
    "description": "TEXT",
    "prize": "TEXT",
    "tags": "TEXT DEFAULT '[]'",
    "source_name": "TEXT DEFAULT ''",
}
# fields copied from the incoming canonical event into the table
TEXT_FIELDS = [c for c in EVENT_COLUMNS if c not in ("tags", "source_name")] + ["source_name"]


def _init_db(con):
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS canonical_events (
            canonical_event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS event_source_links (
            link_id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_event_id INTEGER NOT NULL REFERENCES canonical_events(canonical_event_id),
            source TEXT,
            source_id TEXT NOT NULL UNIQUE,
            source_url TEXT,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL
        );
        """
    )
    # Migrate databases created before these columns existed.
    existing = {row[1] for row in con.execute("PRAGMA table_info(canonical_events)")}
    for column, definition in EVENT_COLUMNS.items():
        if column not in existing:
            con.execute(f"ALTER TABLE canonical_events ADD COLUMN {column} {definition}")


def _provenance_of(event):
    """Return a list of {source, source_id, url} dicts for one canonical event."""
    links = []
    for item in event.get("provenance") or []:
        if item.get("source_id"):
            links.append({"source": item.get("source") or "",
                          "source_id": str(item["source_id"]),
                          "url": item.get("url") or ""})
    if not links:  # fall back to the flat source fields
        ids = event.get("source_ids") or ([event["source_id"]] if event.get("source_id") else [])
        for sid in ids:
            links.append({"source": event.get("source_name") or "", "source_id": str(sid),
                          "url": ""})
    return links


def _clean(value):
    return "" if value is None else str(value)


def _tags_json(event, previous_json="[]"):
    merged = []
    try:
        merged.extend(json.loads(previous_json or "[]"))
    except (TypeError, ValueError):
        pass
    tags = event.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    merged.extend(tags)
    unique, seen = [], set()
    for tag in merged:
        tag = str(tag).strip()
        if tag and tag.casefold() not in seen:
            seen.add(tag.casefold())
            unique.append(tag)
    return json.dumps(unique, ensure_ascii=False)


def save_master(master, db_path=DEFAULT_DB_PATH):
    """Save canonical events + source provenance. Returns {"new", "updated", "total"}."""
    today = date.today().isoformat()
    stats = {"new": 0, "updated": 0}
    con = sqlite3.connect(str(db_path))
    try:
        _init_db(con)
        for event in master:
            links = _provenance_of(event)
            canonical_id = None
            for link in links:  # a known source_id means this event is already in the DB
                row = con.execute("SELECT canonical_event_id FROM event_source_links WHERE source_id = ?",
                                  (link["source_id"],)).fetchone()
                if row:
                    canonical_id = row[0]
                    break

            if canonical_id is None:
                con.execute(
                    "INSERT INTO canonical_events (title, created_at, updated_at) VALUES (?, ?, ?)",
                    (_clean(event.get("title")) or "Untitled event", today, today))
                canonical_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
                previous = {}
                stats["new"] += 1
            else:
                cur = con.execute("SELECT * FROM canonical_events WHERE canonical_event_id = ?", (canonical_id,))
                names = [d[0] for d in cur.description]
                previous = dict(zip(names, cur.fetchone()))
                stats["updated"] += 1

            # new non-empty values win; otherwise keep what the DB already has
            values = {}
            for field in TEXT_FIELDS:
                new_value = _clean(event.get(field))
                old_value = _clean(previous.get(field))
                values[field] = new_value if new_value else old_value
            values["tags"] = _tags_json(event, previous.get("tags") or "[]")
            title = _clean(event.get("title")) or _clean(previous.get("title")) or "Untitled event"

            assignments = ", ".join(f"{k} = ?" for k in values)
            con.execute(
                f"UPDATE canonical_events SET title = ?, {assignments}, updated_at = ? "
                "WHERE canonical_event_id = ?",
                [title, *values.values(), today, canonical_id])

            for link in links:
                con.execute(
                    "INSERT INTO event_source_links (canonical_event_id, source, source_id, source_url, "
                    "first_seen, last_seen) VALUES (?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(source_id) DO UPDATE SET last_seen = excluded.last_seen, "
                    "source_url = CASE WHEN excluded.source_url != '' THEN excluded.source_url "
                    "ELSE event_source_links.source_url END",
                    (canonical_id, link["source"], link["source_id"], link["url"], today, today))
        con.commit()
        stats["total"] = con.execute("SELECT COUNT(*) FROM canonical_events").fetchone()[0]
    finally:
        con.close()
    return stats


# ---------------------------------------------------------------------------
# JSON-list helpers (original lightweight version)
# ---------------------------------------------------------------------------
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
        if key in ("source_ids", "sources", "provenance"):
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
    """Merge a duplicate event or append a new event (JSON-list version)."""
    from dedup import are_duplicates  # imported here to avoid a circular import with dedup.py
    for index, event in enumerate(master_events):
        if are_duplicates(event, new_event):
            master_events[index] = merge_events(event, new_event)
            return master_events
    master_events.append(new_event)
    return master_events
