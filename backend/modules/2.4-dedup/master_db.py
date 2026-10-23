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



def save_master(events, db_path="master_events.db"):
    """Save canonical events to SQLite and migrate older database schemas."""
    import sqlite3
    from datetime import datetime, timezone

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()

    from contextlib import closing

    with closing(sqlite3.connect(str(path))) as con:
        con.execute("PRAGMA foreign_keys = ON")

        con.execute("""
            CREATE TABLE IF NOT EXISTS canonical_events (
                canonical_event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                organizer TEXT,
                start_date TEXT,
                location TEXT,
                registration_link TEXT,
                description TEXT,
                prize TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS event_source_links (
                link_id INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_event_id INTEGER NOT NULL
                    REFERENCES canonical_events(canonical_event_id),
                source TEXT,
                source_id TEXT NOT NULL UNIQUE,
                source_url TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL
            )
        """)

        # Add newer columns to databases created with the older schema.
        existing_columns = {
            row[1]
            for row in con.execute("PRAGMA table_info(canonical_events)")
        }

        new_columns = {
            "end_date": "TEXT",
            "registration_deadline": "TEXT",
            "mode": "TEXT",
            "status": "TEXT",
            "tags": "TEXT NOT NULL DEFAULT '[]'",
            "source_name": "TEXT NOT NULL DEFAULT ''",
        }

        for column, definition in new_columns.items():
            if column not in existing_columns:
                con.execute(
                    f"ALTER TABLE canonical_events "
                    f"ADD COLUMN {column} {definition}"
                )

        new_count = 0
        updated_count = 0

        for event in events:
            title = str(event.get("title") or "Untitled event")

            # Match an existing record before inserting a new one.
            existing = None
            link = event.get("registration_link") or ""

            if link:
                existing = con.execute(
                    """SELECT canonical_event_id
                       FROM canonical_events
                       WHERE registration_link = ?
                       LIMIT 1""",
                    (link,),
                ).fetchone()

            if existing is None:
                existing = con.execute(
                    """SELECT canonical_event_id
                       FROM canonical_events
                       WHERE lower(title) = lower(?)
                         AND COALESCE(start_date, '') = ?
                       LIMIT 1""",
                    (title, str(event.get("start_date") or "")),
                ).fetchone()

            tags = event.get("tags", [])
            if not isinstance(tags, list):
                tags = [tags] if tags else []

            values = (
                title,
                event.get("organizer") or "",
                event.get("start_date") or "",
                event.get("location") or "",
                link,
                event.get("description") or "",
                event.get("prize") or "",
                event.get("end_date") or "",
                event.get("registration_deadline") or "",
                event.get("mode") or "",
                event.get("status") or "",
                json.dumps(tags, ensure_ascii=False),
                event.get("source_name") or "",
            )

            if existing:
                event_id = existing[0]
                con.execute("""
                    UPDATE canonical_events
                    SET title=?, organizer=?, start_date=?, location=?,
                        registration_link=?, description=?, prize=?,
                        end_date=?, registration_deadline=?, mode=?, status=?,
                        tags=?, source_name=?, updated_at=?
                    WHERE canonical_event_id=?
                """, (*values, now, event_id))
                updated_count += 1
            else:
                cursor = con.execute("""
                    INSERT INTO canonical_events (
                        title, organizer, start_date, location,
                        registration_link, description, prize,
                        created_at, updated_at, end_date,
                        registration_deadline, mode, status, tags, source_name
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    *values[:7], now, now, *values[7:]
                ))
                event_id = cursor.lastrowid
                new_count += 1

            # Preserve source provenance where source IDs are available.
            provenance = event.get("provenance", [])
            if not isinstance(provenance, list):
                provenance = []

            for item in provenance:
                if not isinstance(item, dict):
                    continue

                source_id = item.get("source_id")
                if not source_id:
                    continue

                con.execute("""
                    INSERT INTO event_source_links (
                        canonical_event_id, source, source_id, source_url,
                        first_seen, last_seen
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_id) DO UPDATE SET
                        source=excluded.source,
                        source_url=excluded.source_url,
                        last_seen=excluded.last_seen
                """, (
                    event_id,
                    item.get("source") or "",
                    str(source_id),
                    item.get("url") or item.get("source_url") or "",
                    now,
                    now,
                ))
        total = con.execute(
            "SELECT COUNT(*) FROM canonical_events"
        ).fetchone()[0]
        con.commit()
    return {
        "new": new_count,
        "updated": updated_count,
        "total": total,
    }
