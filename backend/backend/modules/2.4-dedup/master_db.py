"""
Saves the merged (canonical) events into a SQLite master database.

Tables
  canonical_events    one row per unique event (what the frontend / ML team reads)
  event_source_links  one row per source listing + provenance (URL, first/last seen)

Running it again does NOT create duplicates: if a source listing (source_id) is already
linked to a canonical event, that event is updated instead of creating a new one.
When the Foundation Team shares their real schema, only this file needs to change.
"""
import sqlite3
from datetime import date

DB_PATH = "master_events.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS canonical_events (
    canonical_event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title              TEXT NOT NULL,
    organizer          TEXT,
    start_date         TEXT,
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


def save_master(master, db_path=DB_PATH):
    today = date.today().isoformat()
    new = updated = 0
    con = sqlite3.connect(db_path)
    try:
        con.executescript(SCHEMA)
        cur = con.cursor()
        for ev in master:
            source_ids = [p["source_id"] for p in ev["provenance"]]

            # Is any of these source listings already linked to a canonical event?
            marks = ",".join("?" * len(source_ids))
            row = cur.execute(
                f"SELECT canonical_event_id FROM event_source_links WHERE source_id IN ({marks}) LIMIT 1",
                source_ids,
            ).fetchone()

            fields = (ev["title"], ev["organizer"], ev["start_date"], ev["location"],
                      ev["registration_link"], ev["description"], ev["prize"])

            if row:
                cid = row[0]
                cur.execute(
                    """UPDATE canonical_events SET title=?, organizer=?, start_date=?, location=?,
                       registration_link=?, description=?, prize=?, updated_at=? WHERE canonical_event_id=?""",
                    fields + (today, cid),
                )
                updated += 1
            else:
                cur.execute(
                    """INSERT INTO canonical_events (title, organizer, start_date, location,
                       registration_link, description, prize, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    fields + (today, today),
                )
                cid = cur.lastrowid
                new += 1

            for p in ev["provenance"]:
                cur.execute(
                    """INSERT INTO event_source_links
                       (canonical_event_id, source, source_id, source_url, first_seen, last_seen)
                       VALUES (?,?,?,?,?,?)
                       ON CONFLICT(source_id) DO UPDATE SET
                         canonical_event_id=excluded.canonical_event_id,
                         source_url=excluded.source_url,
                         last_seen=excluded.last_seen""",
                    (cid, p["source"], p["source_id"], p["url"], today, today),
                )
        con.commit()
        total = cur.execute("SELECT COUNT(*) FROM canonical_events").fetchone()[0]
    finally:
        con.close()
    return {"new": new, "updated": updated, "total": total}
