"""Persist canonical events and source provenance in SQLite.

The schema includes event end date, registration deadline, mode, and status.
Existing databases are migrated additively when save_master() is called.
"""
import json
import sqlite3
from datetime import date

DB_PATH = "master_events.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS canonical_events (
    canonical_event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title              TEXT NOT NULL,
    organizer          TEXT,
    start_date         TEXT,
    end_date           TEXT,
    registration_deadline TEXT,
    mode               TEXT,
    status             TEXT,
    tags               TEXT,
    source_name        TEXT,
    location           TEXT,
    registration_link  TEXT,
    description        TEXT,
    prize              TEXT,
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS event_source_links (
    link_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_event_id INTEGER NOT NULL REFERENCES canonical_events(canonical_event_id),
    source             TEXT,
    source_id          TEXT NOT NULL UNIQUE,
    source_url         TEXT,
    first_seen         TEXT NOT NULL,
    last_seen          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_links_canonical ON event_source_links(canonical_event_id);
"""

MIGRATIONS = {
    "end_date": "TEXT",
    "registration_deadline": "TEXT",
    "mode": "TEXT",
    "status": "TEXT",
    "tags": "TEXT",
    "source_name": "TEXT",
}


def _ensure_columns(cur):
    """Add fields to an older local DB without dropping existing data."""
    existing = {row[1] for row in cur.execute("PRAGMA table_info(canonical_events)")}
    for column, sql_type in MIGRATIONS.items():
        if column not in existing:
            cur.execute(f"ALTER TABLE canonical_events ADD COLUMN {column} {sql_type}")


def save_master(master, db_path=DB_PATH):
    today = date.today().isoformat()
    new = updated = 0
    con = sqlite3.connect(db_path)
    try:
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(SCHEMA)
        cur = con.cursor()
        _ensure_columns(cur)
        for ev in master:
            provenance = ev.get("provenance") or []
            source_ids = [p["source_id"] for p in provenance if p.get("source_id")]
            if not source_ids:
                raise ValueError("Each canonical event must have at least one provenance source_id")

            marks = ",".join("?" * len(source_ids))
            row = cur.execute(
                f"SELECT canonical_event_id FROM event_source_links WHERE source_id IN ({marks}) LIMIT 1",
                source_ids,
            ).fetchone()

            fields = (
                ev.get("title", ""), ev.get("organizer", ""), ev.get("start_date", ""),
                ev.get("end_date", ""), ev.get("registration_deadline", ""),
                ev.get("mode", ""), ev.get("status", ""),
                json.dumps(ev.get("tags", []), ensure_ascii=False),
                ev.get("source_name", ""), ev.get("location", ""),
                ev.get("registration_link", ""), ev.get("description", ""), ev.get("prize", ""),
            )
            if row:
                cid = row[0]
                cur.execute(
                    """UPDATE canonical_events SET title=?, organizer=?, start_date=?, end_date=?,
                       registration_deadline=?, mode=?, status=?, tags=?, source_name=?, location=?, registration_link=?,
                       description=?, prize=?, updated_at=? WHERE canonical_event_id=?""",
                    fields + (today, cid),
                )
                updated += 1
            else:
                cur.execute(
                    """INSERT INTO canonical_events
                       (title, organizer, start_date, end_date, registration_deadline, mode, status, tags, source_name,
                        location, registration_link, description, prize, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    fields + (today, today),
                )
                cid = cur.lastrowid
                new += 1

            for p in provenance:
                if not p.get("source_id"):
                    continue
                cur.execute(
                    """INSERT INTO event_source_links
                       (canonical_event_id, source, source_id, source_url, first_seen, last_seen)
                       VALUES (?,?,?,?,?,?)
                       ON CONFLICT(source_id) DO UPDATE SET
                         canonical_event_id=excluded.canonical_event_id,
                         source=excluded.source,
                         source_url=excluded.source_url,
                         last_seen=excluded.last_seen""",
                    (cid, p.get("source", ""), p["source_id"], p.get("url", ""), today, today),
                )
        con.commit()
        total = cur.execute("SELECT COUNT(*) FROM canonical_events").fetchone()[0]
    finally:
        con.close()
    return {"new": new, "updated": updated, "total": total}
