"""
Module 2.4 - Deduplication, Entity Resolution & Provenance

Run:
    pip install rapidfuzz
    python dedup.py
    python dedup.py events.csv
    python dedup.py events.json
    python dedup.py events.csv --db
"""

import csv
import json
import re
import sys
from datetime import date, datetime
from urllib.parse import urlparse, parse_qsl, urlencode

from rapidfuzz import fuzz


# ---------------- CONFIG ----------------

DUP_THRESHOLD = 80
UNCERTAIN_THRESHOLD = 65
MAX_DATE_DIFF_DAYS = 2
UNCERTAIN_DATE_DAYS = 7
ORG_MIN_SIM = 60

TITLE_ALIASES = {
    "sih": "smart india hackathon",
    "htf": "hack the future",
    "oss": "open source summit",
    "wit": "women in tech",
    "expo": "exhibition",
}

LOCATION_ALIASES = {
    "delhi": "new delhi",
    "new delhi": "new delhi",
    "dilli": "new delhi",
    "iit delhi": "new delhi",
    "iit d": "new delhi",
    "iitd": "new delhi",
    "bangalore": "bengaluru",
    "bengaluru": "bengaluru",
    "bangaluru": "bengaluru",
    "hyd": "hyderabad",
    "hyderabad": "hyderabad",
    "online": "online",
    "virtual": "online",
}

DATE_FORMATS = [
    "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y",
    "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y"
]

FIELD_MAP = {
    "source": ["source", "source_name", "site", "platform"],
    "source_id": ["source_id", "id", "event_id"],
    "source_url": ["source_url", "url", "page_url", "event_url", "public_url"],
    "title": ["title", "name", "event_name", "opportunity_name"],
    "organizer": ["organizer", "organiser", "host", "organized_by",
                  "organizer_name", "organisation_name", "organization_name"],
    "start_date": ["start_date", "date_start", "startdate", "date"],
    "location": ["location", "city", "venue"],
    "registration_link": ["registration_link", "register_url",
                          "registration_url", "apply_link"],
    "description": ["description", "desc", "about"],
    "prize": ["prize", "prize_pool", "prizes", "prize_amount"],
    "end_date": ["end_date", "date_end", "enddate", "event_end_date"],
    "registration_deadline": ["registration_deadline", "deadline",
                              "last_date_to_register", "registration_end_date"],
    "mode": ["mode", "event_mode", "delivery_mode"],
    "status": ["status", "event_status", "opportunity_status"],
    "tags": ["tags", "keywords", "categories", "skills"],
}

SAMPLE = [
    {
        "source": "sample",
        "source_id": "1",
        "title": "AI Hackathon",
        "organizer": "ABC University",
        "start_date": "2026-11-10",
        "location": "Hyderabad",
        "registration_link": "https://example.com/register",
        "description": "Artificial intelligence hackathon",
        "prize": "10000",
    },
    {
        "source": "sample",
        "source_id": "2",
        "title": "AI Hackathon",
        "organizer": "ABC University",
        "start_date": "2026-11-10",
        "location": "Hyderabad",
        "registration_link": "https://example.com/register",
        "description": "AI event",
        "prize": "10000",
    },
]


# ---------------- NORMALIZATION ----------------

def clean_text(value):
    value = str(value or "").strip().casefold()
    return re.sub(r"\s+", " ", value)


def normalize_text(value):
    return re.sub(r"[^a-z0-9 ]", "", clean_text(value))


def to_iso(value):
    value = str(value or "").strip()
    if not value:
        return ""

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).date().isoformat()
    except ValueError:
        pass

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass

    return ""


def normalize_link(value):
    value = str(value or "").strip()
    if not value:
        return ""

    try:
        parsed = urlparse(value)
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        query = urlencode(sorted(parse_qsl(parsed.query)))
        return f"{scheme}://{netloc}{path}" + (f"?{query}" if query else "")
    except Exception:
        return value.rstrip("/")


def normalize_location(value):
    value = normalize_text(value)
    return LOCATION_ALIASES.get(value, value)


def normalize_title(value):
    value = normalize_text(value)
    words = value.split()
    return " ".join(TITLE_ALIASES.get(word, word) for word in words)


def map_record(raw, index):
    """Convert an input record into the standard event format."""
    if not isinstance(raw, dict):
        raise ValueError(f"Record {index} must be a JSON object")

    lower = {str(k).strip().lower(): v for k, v in raw.items()}
    record = {}

    for field, aliases in FIELD_MAP.items():
        record[field] = ""
        for alias in aliases:
            if alias in lower and lower[alias] not in (None, ""):
                record[field] = lower[alias]
                break

    record["source"] = str(record["source"] or "unknown").strip()
    record["source_id"] = str(record["source_id"] or index).strip()
    record["source_url"] = str(record["source_url"] or "").strip()
    record["title"] = str(record["title"] or "").strip()
    record["organizer"] = str(record["organizer"] or "").strip()
    record["start_date"] = to_iso(record["start_date"])
    record["end_date"] = to_iso(record["end_date"])
    record["registration_deadline"] = to_iso(
        record["registration_deadline"]
    )
    record["location"] = str(record["location"] or "").strip()
    record["registration_link"] = str(
        record["registration_link"] or ""
    ).strip()
    record["description"] = str(record["description"] or "").strip()
    record["prize"] = record["prize"] or ""
    record["mode"] = str(record["mode"] or "").strip()
    record["status"] = str(record["status"] or "").strip()

    tags = record["tags"]
    if isinstance(tags, str):
        tags = [x.strip() for x in tags.split(",") if x.strip()]
    record["tags"] = tags or []

    return record


# ---------------- COMPARISON ----------------

def dates_match(date_a, date_b, tolerance_days=MAX_DATE_DIFF_DAYS):
    if not date_a or not date_b:
        return False

    try:
        a = datetime.strptime(date_a, "%Y-%m-%d").date()
        b = datetime.strptime(date_b, "%Y-%m-%d").date()
        return abs((a - b).days) <= tolerance_days
    except ValueError:
        return False


def compare(a, b, title_threshold=DUP_THRESHOLD):
    """Return duplicate, different, or uncertain with a reason."""

    link_a = normalize_link(a.get("registration_link") or a.get("source_url"))
    link_b = normalize_link(b.get("registration_link") or b.get("source_url"))

    if link_a and link_b and link_a == link_b:
        return "duplicate", "exact registration link match"

    title_a = normalize_title(a.get("title"))
    title_b = normalize_title(b.get("title"))

    if not title_a or not title_b:
        return "uncertain", "missing title"

    title_score = fuzz.token_set_ratio(title_a, title_b)

    org_a = normalize_text(a.get("organizer"))
    org_b = normalize_text(b.get("organizer"))

    if org_a and org_b:
        org_score = fuzz.token_set_ratio(org_a, org_b)
    else:
        org_score = 0

    location_a = normalize_location(a.get("location"))
    location_b = normalize_location(b.get("location"))

    date_a = to_iso(a.get("start_date"))
    date_b = to_iso(b.get("start_date"))

    if title_score >= title_threshold:
        if org_a and org_b and org_score < ORG_MIN_SIM:
            return "different", "organizers are different"

        if location_a and location_b and location_a != location_b:
            return "different", "locations are different"

        if date_a and date_b:
            if dates_match(date_a, date_b, MAX_DATE_DIFF_DAYS):
                return "duplicate", "title, organizer, location and date match"

            if dates_match(date_a, date_b, UNCERTAIN_DATE_DAYS):
                return "uncertain", "dates are close but outside duplicate tolerance"

            return "different", "event dates are different"

        return "uncertain", "date information is missing"

    if title_score >= UNCERTAIN_THRESHOLD:
        if date_a and date_b and dates_match(
            date_a, date_b, UNCERTAIN_DATE_DAYS
        ):
            return "uncertain", "similar titles and nearby dates"

    return "different", "insufficient similarity"


# ---------------- CLUSTERING ----------------

def cluster(events):
    """Group duplicate events and retain uncertain pairs for review."""
    parent = list(range(len(events)))
    uncertain = []

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(events)):
        for j in range(i + 1, len(events)):
            label, reason = compare(events[i], events[j])

            if label == "duplicate":
                left = [
                    k for k in range(len(events))
                    if find(k) == find(i)
                ]
                right = [
                    k for k in range(len(events))
                    if find(k) == find(j)
                ]

                if all(
                    compare(events[x], events[y])[0] == "duplicate"
                    for x in left for y in right
                ):
                    parent[find(i)] = find(j)
                else:
                    uncertain.append({
                        "id_a": events[i]["source_id"],
                        "id_b": events[j]["source_id"],
                        "reason": "conflicting cluster members; manual review required",
                    })

            elif label == "uncertain":
                uncertain.append({
                    "id_a": events[i]["source_id"],
                    "id_b": events[j]["source_id"],
                    "title_a": events[i]["title"],
                    "title_b": events[j]["title"],
                    "reason": reason,
                })

    groups = {}
    for i in range(len(events)):
        groups.setdefault(find(i), []).append(events[i])

    return list(groups.values()), uncertain


def are_duplicates(a, b, title_threshold=DUP_THRESHOLD):
    """Compatibility entry point for the labeled-pair evaluator."""
    return compare(
        map_record(a, 0),
        map_record(b, 1),
        title_threshold
    )[0] == "duplicate"


# ---------------- MERGE ----------------

def to_num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def merge_group(group, canonical_id):
    best_title = max(
        group, key=lambda e: len(e.get("title", ""))
    ).get("title", "")

    best_desc = max(
        group, key=lambda e: len(e.get("description") or "")
    ).get("description", "")

    best_prize = max(
        group, key=lambda e: to_num(e.get("prize"))
    ).get("prize", "")

    def first(key):
        return next((e.get(key) for e in group if e.get(key)), "")

    merged_tags = []
    for event in group:
        tags = event.get("tags", [])
        if isinstance(tags, str):
            tags = [part.strip() for part in tags.split(",") if part.strip()]

        for tag in tags or []:
            tag = str(tag).strip()
            if tag and tag.casefold() not in {
                x.casefold() for x in merged_tags
            }:
                merged_tags.append(tag)

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
            {
                "source": e["source"],
                "source_id": e["source_id"],
                "url": e["source_url"],
                "seen_on": date.today().isoformat(),
            }
            for e in group
        ],
    }


# ---------------- INPUT LOADING ----------------

def load(path):
    if path.lower().endswith(".json"):
        with open(path, encoding="utf-8-sig") as file:
            raw = json.load(file)

        while isinstance(raw, dict):
            next_value = None
            for key in (
                "events", "opportunities", "results",
                "data", "items", "records"
            ):
                value = raw.get(key)
                if isinstance(value, (list, dict)):
                    next_value = value
                    break

            if next_value is None:
                raise ValueError(
                    "JSON must contain event records under events/data/results/items/records"
                )

            raw = next_value

        if not isinstance(raw, list):
            raise ValueError("JSON input must resolve to a list")

    else:
        with open(path, newline="", encoding="utf-8-sig") as file:
            raw = list(csv.DictReader(file))

    return [map_record(record, i) for i, record in enumerate(raw)]


# ---------------- MAIN ----------------

def main():
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    save_db = "--db" in sys.argv

    if args:
        events = load(args[0])
    else:
        events = [map_record(record, i) for i, record in enumerate(SAMPLE)]

    groups, uncertain = cluster(events)

    master = [
        merge_group(group, 101 + number)
        for number, group in enumerate(groups)
    ]

    with open("master_events.json", "w", encoding="utf-8") as file:
        json.dump(master, file, indent=2, ensure_ascii=False)

    with open("uncertain_pairs.json", "w", encoding="utf-8") as file:
        json.dump(uncertain, file, indent=2, ensure_ascii=False)

    print(f"Input events : {len(events)}")
    print(
        f"Master events: {len(master)} "
        f"(duplicates removed: {len(events) - len(master)})"
    )
    print(f"Uncertain    : {len(uncertain)} pairs -> uncertain_pairs.json\n")

    for event in master:
        print(
            f"[{event['canonical_event_id']}] "
            f"{event['title']} | {event['start_date']} | "
            f"{event['location']} | sources={event['source_ids']}"
        )

    if save_db:
        from master_db import save_master
        stats = save_master(master)
        print(
            f"\nSaved to master_events.db -> "
            f"new: {stats['new']}, updated: {stats['updated']}, "
            f"total in DB: {stats['total']}"
        )


if __name__ == "__main__":
    main()
