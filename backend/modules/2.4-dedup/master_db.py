            for source, source_id in identities:
                source_url = next(
                    (
                        _clean(item.get("url"))
                        for item in provenance
                        if str(item.get("source") or "").strip() == source
                        and str(item.get("source_id") or "").strip() == source_id
                    ),
                    "",
                )
                cur.execute(
                    """INSERT INTO event_source_links
                       (canonical_event_id, source, source_id, source_url,
                        first_seen, last_seen)
                       VALUES (?,?,?,?,?,?)
                       ON CONFLICT(source, source_id) DO UPDATE SET
                           canonical_event_id=excluded.canonical_event_id,
                           source_url=CASE
                               WHEN excluded.source_url != ''
                               THEN excluded.source_url
                               ELSE event_source_links.source_url
                           END,
                           last_seen=excluded.last_seen""",
                    (canonical_id, source, source_id, source_url, today, today),
                )

            snapshot_fields = {
                "title": fields[0],
                "organizer": fields[1],
                "start_date": fields[2],
                "end_date": fields[3],
                "registration_deadline": fields[4],
                "mode": fields[5],
                "status": fields[6],
                "tags": tags,
                "source_name": fields[8],
                "location": fields[9],
                "registration_link": fields[10],
                "description": fields[11],
                "prize": fields[12],
                "provenance": [
                    {"source": item[0], "source_id": item[1], "url": item[2]}
                    for item in cur.execute(
                        """SELECT source, source_id, source_url
                           FROM event_source_links
                           WHERE canonical_event_id = ?
                           ORDER BY source, source_id""",
                        (canonical_id,),
                    )
                ],
            }
            snapshot = json.dumps(
                snapshot_fields, sort_keys=True, ensure_ascii=False
            )
            last = cur.execute(
                """SELECT snapshot FROM event_versions
                   WHERE canonical_event_id = ?
                   ORDER BY version_id DESC LIMIT 1""",
                (canonical_id,),
            ).fetchone()
            if last is None or last[0] != snapshot:
                cur.execute(
                    """INSERT INTO event_versions
                       (canonical_event_id, snapshot, observed_at)
                       VALUES (?, ?, ?)""",
                    (canonical_id, snapshot, today),
                )

        con.commit()
        total = cur.execute(
            "SELECT COUNT(*) FROM canonical_events"
        ).fetchone()[0]
    finally:
        con.close()

    return {"new": new, "updated": updated, "total": total}


# Backwards-compatible JSON-list helpers.
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
    from dedup import are_duplicates
    for index, event in enumerate(master_events):
        if are_duplicates(event, new_event):
            master_events[index] = merge_events(event, new_event)
