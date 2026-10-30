"""
Module 2.4 - Master database integration.
 
* save_master()       -> SQLite master DB: canonical_events + event_source_links
                         (provenance) + event_versions (change history).
* update_master_db()  -> lightweight JSON-list helpers (load_events / save_events /
                         merge_events), kept for backwards compatibility.
 
Provenance is never lost: every (source, source_id) pair is stored in
event_source_links. Re-running with a known (source, source_id) updates the
existing canonical event instead of creating a duplicate.
"""
import json
import sqlite3
from datetime import date
from pathlib import Path
 
DEFAULT_DB_PATH = "master_events.db"
 
# Columns that may be missing in older databases (added automatically).
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
TEXT_FIELDS = [c for c in EVENT_COLUMNS if c != "tags"]
 
 
def _clean(value):
    return "" if value is None else str(value).strip()
 
 
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
            canonical_event_id INTEGER NOT NULL
                REFERENCES canonical_events(canonical_event_id),
            source TEXT NOT NULL DEFAULT '',
            source_id TEXT NOT NULL,
            source_url TEXT,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS event_versions (
            version_id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_event_id INTEGER NOT NULL
                REFERENCES canonical_events(canonical_event_id),
            snapshot TEXT NOT NULL,
            observed_at TEXT NOT NULL
        );
        """
    )
    # Migrate databases created before these columns existed.
    existing = {row[1] for row in con.execute("PRAGMA table_info(canonical_events)")}
    for column, definition in EVENT_COLUMNS.items():
        if column not in existing:
            con.execute(f"ALTER TABLE canonical_events ADD COLUMN {column} {definition}")
    # ON CONFLICT(source, source_id) needs this unique index (also on old databases).
    con.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_source_identity "
        "ON event_source_links(source, source_id)"
    )
 
 
def _identities(event):
    """Return [(source, source_id, url)] for one canonical event."""
    found, seen = [], set()
    for item in event.get("provenance") or []:
        source_id = _clean(item.get("source_id"))
        if not source_id:
            continue
        key = (_clean(item.get("source")), source_id)
        if key not in seen:
            seen.add(key)
            found.append((key[0], key[1], _clean(item.get("url"))))
    if not found:  # fall back to the flat source fields
        ids = event.get("source_ids") or ([event["source_id"]] if event.get("source_id") else [])
        for source_id in ids:
            key = (_clean(event.get("source_name")), _clean(source_id))
            if key[1] and key not in seen:
                seen.add(key)
                found.append((key[0], key[1], ""))
    return found
 
 
def _merge_tags(event, previous_json):
    try:
        merged = list(json.loads(previous_json or "[]"))
    except (TypeError, ValueError):
        merged = []
    tags = event.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    merged.extend(tags)
    unique, seen = [], set()
    for tag in merged:
        tag = _clean(tag)
        if tag and tag.casefold() not in seen:
            seen.add(tag.casefold())
            unique.append(tag)
    return unique
 
 
def save_master(master, db_path=DEFAULT_DB_PATH):
    """Save canonical events + provenance. Returns {"new", "updated", "total"}."""
    today = date.today().isoformat()
    new = updated = 0
    con = sqlite3.connect(str(db_path))
    try:
        _init_db(con)
        cur = con.cursor()
        for event in master:
            identities = _identities(event)
 
            # Is any of these (source, source_id) pairs already in the DB?
            canonical_id = None
            for source, source_id, _ in identities:
                row = cur.execute(
                    "SELECT canonical_event_id FROM event_source_links "
                    "WHERE source = ? AND source_id = ?", (source, source_id)).fetchone()
                if row:
                    canonical_id = row[0]
                    break
 
            if canonical_id is None:
                cur.execute(
                    "INSERT INTO canonical_events (title, created_at, updated_at) VALUES (?, ?, ?)",
                    (_clean(event.get("title")) or "Untitled event", today, today))
                canonical_id = cur.lastrowid
                previous = {}
                new += 1
            else:
                fetched = cur.execute(
                    "SELECT * FROM canonical_events WHERE canonical_event_id = ?",
                    (canonical_id,))
                names = [d[0] for d in fetched.description]
                previous = dict(zip(names, fetched.fetchone()))
                updated += 1
 
            # Non-empty new values win; empty ones keep what the DB already has.
            values = {f: _clean(event.get(f)) or _clean(previous.get(f)) for f in TEXT_FIELDS}
            tags = _merge_tags(event, previous.get("tags"))
            values["tags"] = json.dumps(tags, ensure_ascii=False)
            title = _clean(event.get("title")) or _clean(previous.get("title")) or "Untitled event"
 
            assignments = ", ".join(f"{column} = ?" for column in values)
            cur.execute(
                f"UPDATE canonical_events SET title = ?, {assignments}, updated_at = ? "
                "WHERE canonical_event_id = ?",
                [title, *values.values(), today, canonical_id])
 
            for source, source_id, source_url in identities:
                cur.execute(
                    """INSERT INTO event_source_links
                       (canonical_event_id, source, source_id, source_url, first_seen, last_seen)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT(source, source_id) DO UPDATE SET
                           canonical_event_id = excluded.canonical_event_id,
                           source_url = CASE WHEN excluded.source_url != ''
                                             THEN excluded.source_url
                                             ELSE event_source_links.source_url END,
                           last_seen = excluded.last_seen""",
                    (canonical_id, source, source_id, source_url, today, today))
 
            # Version history: store a snapshot only when something changed.
            snapshot_data = {"title": title, **{k: v for k, v in values.items() if k != "tags"},
                             "tags": tags,
                             "provenance": [
                                 {"source": r[0], "source_id": r[1], "url": r[2]}
                                 for r in cur.execute(
                                     "SELECT source, source_id, source_url FROM event_source_links "
                                     "WHERE canonical_event_id = ? ORDER BY source, source_id",
                                     (canonical_id,)).fetchall()]}
            snapshot = json.dumps(snapshot_data, sort_keys=True, ensure_ascii=False)
            last = cur.execute(
                "SELECT snapshot FROM event_versions WHERE canonical_event_id = ? "
                "ORDER BY version_id DESC LIMIT 1", (canonical_id,)).fetchone()
            if last is None or last[0] != snapshot:
                cur.execute(
                    "INSERT INTO event_versions (canonical_event_id, snapshot, observed_at) "
                    "VALUES (?, ?, ?)", (canonical_id, snapshot, today))
 
        con.commit()
        total = cur.execute("SELECT COUNT(*) FROM canonical_events").fetchone()[0]
    finally:
        con.close()
 
    return {"new": new, "updated": updated, "total": total}
 
 
# ---------------------------------------------------------------------------
# Backwards-compatible JSON-list helpers
# ---------------------------------------------------------------------------
def load_events(file_path):
    path = Path(file_path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file:
        events = json.load(file)
    if not isinstance(events, list):
        raise ValueError("Master database must contain a JSON list.")
    return events
 
 
def save_events(events, file_path):
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(events, file, indent=4, ensure_ascii=False)
 
 
def merge_events(existing, new_event):
    """Merge event details while retaining all source provenance."""
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
    from dedup import are_duplicates  # imported here to avoid a circular import
    for index, event in enumerate(master_events):
        if are_duplicates(event, new_event):
            master_events[index] = merge_events(event, new_event)
            return master_events
    master_events.append(new_event)
    return master_events
 
