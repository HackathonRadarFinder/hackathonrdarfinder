            right = [k for k in range(len(events)) if find(k) == find(j)]
            if all(compare(events[x], events[y])[0] == "duplicate" for x in left for y in right):
                parent[find(i)] = find(j)
            else:
                uncertain.append({"id_a": events[i]["source_id"], "id_b": events[j]["source_id"],
                                  "reason": "conflicting cluster members; manual review required"})
        elif label == "uncertain":
            uncertain.append({"id_a": events[i]["source_id"], "id_b": events[j]["source_id"],
                              "title_a": events[i]["title"], "title_b": events[j]["title"],
                              "reason": reason})
    groups = {}
    for i in range(len(events)):
        groups.setdefault(find(i), []).append(events[i])
    return list(groups.values()), uncertain


def are_duplicates(a, b, title_threshold=DUP_THRESHOLD):
    """Compatibility entry point for the labeled-pair evaluator."""
    return compare(map_record(a, 0), map_record(b, 1), title_threshold)[0] == "duplicate"

# ---------------- MERGE ----------------
def to_num(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def merge_group(group, canonical_id):
    best_title = max(group, key=lambda e: len(e["title"]))["title"]
    best_desc = max(group, key=lambda e: len(e.get("description") or ""))["description"]
    best_prize = max(group, key=lambda e: to_num(e.get("prize")))["prize"]
    first = lambda k: next((e[k] for e in group if e.get(k)), "")
    merged_tags = []
    for event in group:
        tags = event.get("tags", [])
        if isinstance(tags, str):
            tags = [part.strip() for part in tags.split(",") if part.strip()]
        for tag in tags or []:
            if str(tag).strip() and str(tag).strip().casefold() not in {x.casefold() for x in merged_tags}:
                merged_tags.append(str(tag).strip())
    return {
        "canonical_event_id": canonical_id,
        "title": best_title,
        "organizer": first("organizer"),
        "description": best_desc,
        "start_date": first("start_date"),
        "end_date": first("end_date"),
        "location": first("location"),
        "mode": first("mode"),
        "registration_link": first("registration_link"),
        "prize": best_prize,
        "tags": merged_tags,
        "source_id": first("source_id"),
        "source_name": first("source"),
        "status": first("status"),
        "registration_deadline": first("registration_deadline"),
        "source_ids": [e["source_id"] for e in group],
        "provenance": [
            {"source": e["source"], "source_id": e["source_id"], "url": e["source_url"],
             "seen_on": date.today().isoformat()} for e in group
        ],
    }

# ---------------- MAIN ----------------
def load(path):
    if path.lower().endswith(".json"):
        with open(path, encoding="utf-8-sig") as f:
            raw = json.load(f)
        # Accept direct lists and common API/export wrappers.
        while isinstance(raw, dict):
            next_value = None
            for key in ("events", "opportunities", "results", "data", "items", "records"):
                value = raw.get(key)
                if isinstance(value, (list, dict)):
                    next_value = value
                    break
            if next_value is None:
                raise ValueError("JSON must contain a list of event records (directly or under events/data/results/items/records)")
            raw = next_value
        if not isinstance(raw, list):
            raise ValueError("JSON input must resolve to a list of event records")
    else:
        with open(path, newline="", encoding="utf-8-sig") as f:
            raw = list(csv.DictReader(f))
    return [map_record(r, i) for i, r in enumerate(raw)]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    save_db = "--db" in sys.argv
    if args:
        events = load(args[0])
    else:
        events = [map_record(r, i) for i, r in enumerate(SAMPLE)]
    groups, uncertain = cluster(events)
    master = [merge_group(g, 101 + n) for n, g in enumerate(groups)]


    with open("master_events.json", "w", encoding="utf-8") as f:
        json.dump(master, f, indent=2, ensure_ascii=False)
    with open("uncertain_pairs.json", "w", encoding="utf-8") as f:
        json.dump(uncertain, f, indent=2, ensure_ascii=False)

    print(f"Input events : {len(events)}")
    print(f"Master events: {len(master)}  (duplicates removed: {len(events) - len(master)})")
    print(f"Uncertain    : {len(uncertain)} pairs -> uncertain_pairs.json\n")
    for m in master:
        print(f"[{m['canonical_event_id']}] {m['title']} | {m['start_date']} | {m['location']} | sources={m['source_ids']}")

    if save_db:
        from master_db import save_master
        stats = save_master(master)
        print(f"\nSaved to master_events.db -> new: {stats['new']}, updated: {stats['updated']}, total in DB: {stats['total']}")


if __name__ == "__main__":
    main()

