"""Persist canonical events and source provenance in SQLite.

The schema includes event end date, registration deadline, mode, and status.
Existing databases are migrated additively when save_master() is called.
"""
import json
import sqlite3
from datetime import date
from dedup import compare, map_record

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
    source_id          TEXT NOT NULL,
    source_url         TEXT,
    first_seen         TEXT NOT NULL,
    last_seen          TEXT NOT NULL,
    UNIQUE(source, source_id)
);

CREATE INDEX IF NOT EXISTS idx_links_canonical ON event_source_links(canonical_event_id);
CREATE TABLE IF NOT EXISTS event_versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_event_id INTEGER NOT NULL REFERENCES canonical_events(canonical_event_id),
    snapshot TEXT NOT NULL,
    observed_at TEXT NOT NULL
);
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
    # Preserve older rows while replacing globally unique IDs with platform-scoped IDs.
    indexes = list(cur.execute("PRAGMA index_list(event_source_links)"))
    old_unique = any(row[2] and [x[2] for x in cur.execute(f'PRAGMA index_info("{row[1]}")')] == ["source_id"] for row in indexes)
    if old_unique:
        cur.execute("ALTER TABLE event_source_links RENAME TO legacy_source_links")
        cur.execute("""CREATE TABLE event_source_links (
            link_id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_event_id INTEGER NOT NULL REFERENCES canonical_events(canonical_event_id),
            source TEXT, source_id TEXT NOT NULL, source_url TEXT,
            first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, UNIQUE(source,source_id))""")
        cur.execute("INSERT INTO event_source_links SELECT * FROM legacy_source_links")
        cur.execute("DROP TABLE legacy_source_links")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_links_canonical ON event_source_links(canonical_event_id)")


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
            incoming = ev
            provenance = ev.get("provenance") or []
            identities = [(p.get("source", ""), p["source_id"]) for p in provenance if p.get("source_id")]
            if not identities or any(not source for source, _ in identities):
                raise ValueError("Each canonical event must have at least one provenance source_id")
            matches = {r[0] for identity in identities for r in cur.execute(
                "SELECT canonical_event_id FROM event_source_links WHERE source=? AND source_id=?", identity)}
            if len(matches) > 1:
                raise ValueError("Merge spans existing canonical events; manual review required")
            row = (next(iter(matches)),) if matches else None
            # Resolve duplicate listings arriving in later batches without conflating source IDs.
            if row is None:
                columns = [r[1] for r in cur.execute("PRAGMA table_info(canonical_events)")]
                candidates = []
                for stored in cur.execute("SELECT * FROM canonical_events").fetchall():
                    old = dict(zip(columns, stored))
                    if compare(map_record(old, 0), map_record(ev, 1))[0] == "duplicate":
                        candidates.append(old["canonical_event_id"])
                if len(candidates) > 1:
                    raise ValueError("Multiple persisted duplicate candidates; manual review required")
                if candidates:
                    row = (candidates[0],)

            previous = None
            if row:
                columns = [r[1] for r in cur.execute("PRAGMA table_info(canonical_events)")]
                previous = dict(zip(columns, cur.execute("SELECT * FROM canonical_events WHERE canonical_event_id=?", row).fetchone()))
                if compare(map_record(previous, 0), map_record(ev, 1))[1] == "conflicting edition dates or years":
                    raise ValueError("Source identity was reused for a conflicting edition; manual review required")
                # A subsequent source must not erase richer existing metadata.
                ev = dict(ev)
                for key, value in previous.items():
                    if key not in {"canonical_event_id", "created_at", "updated_at", "tags"} and not ev.get(key):
                        ev[key] = value
                old_tags = json.loads(previous.get("tags") or "[]")
                ev["tags"] = list(dict.fromkeys(old_tags + ev.get("tags", [])))

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

            incoming["canonical_event_id"] = cid

            for p in provenance:
                if not p.get("source_id"):
                    continue
                cur.execute(
                    """INSERT INTO event_source_links
                       (canonical_event_id, source, source_id, source_url, first_seen, last_seen)
                       VALUES (?,?,?,?,?,?)
                       ON CONFLICT(source, source_id) DO UPDATE SET
                         canonical_event_id=excluded.canonical_event_id,
                         source=excluded.source,
                         source_url=excluded.source_url,
                         last_seen=excluded.last_seen""",
                    (cid, p.get("source", ""), p["source_id"], p.get("url", ""), today, today),
                )
            snapshot_fields = dict(zip(("title", "organizer", "start_date", "end_date", "registration_deadline",
                "mode", "status", "tags", "source_name", "location", "registration_link", "description", "prize"), fields))
            snapshot_fields["provenance"] = [dict(source=r[0], source_id=r[1], url=r[2]) for r in cur.execute(
                "SELECT source,source_id,source_url FROM event_source_links WHERE canonical_event_id=? ORDER BY source,source_id", (cid,))]
            snapshot = json.dumps(snapshot_fields, sort_keys=True, ensure_ascii=False)
            last = cur.execute("SELECT snapshot FROM event_versions WHERE canonical_event_id=? ORDER BY version_id DESC LIMIT 1", (cid,)).fetchone()
            if last is None or last[0] != snapshot:
                cur.execute("INSERT INTO event_versions(canonical_event_id,snapshot,observed_at) VALUES (?,?,?)", (cid,snapshot,today))
        con.commit()
        total = cur.execute("SELECT COUNT(*) FROM canonical_events").fetchone()[0]
    finally:
        con.close()
    return {"new": new, "updated": updated, "total": total}
