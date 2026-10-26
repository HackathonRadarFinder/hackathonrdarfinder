"""
Module 2.4 - Deduplication, Entity Resolution & Provenance
Run:  pip install rapidfuzz
      python dedup.py                 (uses built-in sample data)
      python dedup.py events.csv      (uses your own CSV)

CSV columns expected:
source, source_id, source_url, title, organizer, start_date (YYYY-MM-DD),
location, registration_link, description, prize
"""
import csv
import json
import re
import sys
from datetime import date, datetime
from collections import defaultdict
from urllib.parse import urlparse, parse_qsl, urlencode

from rapidfuzz import fuzz

# ---------------- CONFIG (tune using your 20 labeled pairs) ----------------
DUP_THRESHOLD = 80        # title similarity >= this -> duplicate
UNCERTAIN_THRESHOLD = 65  # between this and DUP_THRESHOLD -> uncertain
MAX_DATE_DIFF_DAYS = 2
UNCERTAIN_DATE_DAYS = 7   # for uncertain pairs, dates must be this close
ORG_MIN_SIM = 60          # organizers less similar than this -> different events

TITLE_ALIASES = {
    "sih": "smart india hackathon",
    "htf": "hack the future",
    "oss": "open source summit",
    "wit": "women in tech",
    "expo": "exhibition",
}
LOCATION_ALIASES = {
    "delhi": "new delhi", "new delhi": "new delhi", "dilli": "new delhi",
    "iit delhi": "new delhi", "iit d": "new delhi", "iitd": "new delhi",
    "bangalore": "bengaluru", "bengaluru": "bengaluru", "bangaluru": "bengaluru",
    "hyd": "hyderabad", "hyderabad": "hyderabad",
    "online": "online", "virtual": "online",
}

LOCATION_STOPWORDS = {"india", "nit", "iit", "iiit", "iim", "university", "college", "campus",
                      "institute", "of", "technology", "the", "and"}
ORG_STOPWORDS = {"organizer", "organiser", "host", "college", "university", "institute", "institution", "club", "organization",
                 "organisation", "org", "team", "society", "association", "department", "dept",
                 "chapter", "foundation", "group", "the", "of", "and"}

# ---------------- INPUT FORMAT (edit this when Shivam shares his format) ----------------
# left side = the names this script uses; right side = names that may appear in the input file.
# If Shivam's output uses a different name, just add it to the list.
FIELD_MAP = {
    "source":            ["source", "source_name", "site", "platform"],
    "source_id":         ["source_id", "id", "event_id"],
    "source_url":        ["source_url", "url", "page_url", "event_url", "public_url"],
    "title":             ["title", "name", "event_name", "opportunity_name"],
    "organizer":         ["organizer", "organiser", "host", "organized_by", "organizer_name", "organisation_name", "organization_name"],
    "start_date":        ["start_date", "date_start", "startdate", "date"],
    "location":          ["location", "city", "venue"],
    "registration_link": ["registration_link", "register_url", "registration_url", "apply_link"],
    "description":       ["description", "desc", "about"],
    "prize":             ["prize", "prize_pool", "prizes", "prize_amount"],
    "end_date":          ["end_date", "date_end", "enddate", "event_end_date"],
    "registration_deadline": ["registration_deadline", "deadline", "last_date_to_register", "registration_end_date"],
    "mode":              ["mode", "event_mode", "delivery_mode"],
    "status":            ["status", "event_status", "opportunity_status"],
    "tags":              ["tags", "keywords", "categories", "skills"],
}

DATE_FORMATS = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y"]


def to_iso(value):
    """Convert common date/date-time formats to YYYY-MM-DD (empty if unreadable)."""
    value = (value or "").strip()
    if not value:
        return ""
    # Accept ISO dates, ISO timestamps, and timestamps ending in Z/offset.
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        pass
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def map_record(raw, index):
    """Turn one raw input record into the field names used by this script."""
    if not isinstance(raw, dict):
        raise ValueError(f"Record {index} must be a JSON object")
    lower = {str(k).strip().lower(): v for k, v in raw.items()}
    rec = {}
    for field, names in FIELD_MAP.items():
        rec[field] = ""
        for n in names:
            value = lower.get(n)
            if value not in (None, ""):
                rec[field] = value if field == "tags" and isinstance(value, list) else str(value).strip()
                break
    # Module 2.3 canonical schema allows tags as a list of strings.
    raw_tags = rec.get("tags", "")
    if isinstance(raw_tags, list):
        tags = raw_tags
    elif isinstance(raw_tags, str) and raw_tags.strip():
        # JSON-encoded arrays are common in CSV exports; otherwise split on commas.
        try:
            parsed_tags = json.loads(raw_tags)
            tags = parsed_tags if isinstance(parsed_tags, list) else [raw_tags]
        except (json.JSONDecodeError, TypeError):
            tags = [part.strip() for part in raw_tags.split(",") if part.strip()]
    else:
        tags = []
    rec["tags"] = list(dict.fromkeys(str(tag).strip() for tag in tags if str(tag).strip()))
    rec["start_date"] = to_iso(rec["start_date"])
    rec["end_date"] = to_iso(rec["end_date"])
    rec["registration_deadline"] = to_iso(rec["registration_deadline"])
    rec["source"] = rec["source"] or "unknown"
    rec["source_id"] = rec["source_id"] or f"{rec['source']}_row_{index}"
    rec["source_url"] = rec["source_url"] or rec["registration_link"]
    return rec

# ---------------- SAMPLE DATA ----------------
SAMPLE = [
    {"source": "unstop", "source_id": "unstop_123", "source_url": "https://unstop.com/hackathons/hack-the-future-123",
     "title": "Hack The Future", "organizer": "IIT Delhi", "start_date": "2026-02-10",
     "location": "IIT Delhi", "registration_link": "https://unstop.com/hackathons/hack-the-future-123?utm_source=x",
     "description": "A 36-hour hackathon on AI, climate and open innovation with mentors from industry.", "prize": "50000"},
    {"source": "devfolio", "source_id": "devfolio_456", "source_url": "https://devfolio.co/htf-2026",
     "title": "HTF 2026", "organizer": "IIT-D", "start_date": "2026-02-10",
     "location": "IIT-D", "registration_link": "https://htf2026.devfolio.co",
     "description": "Hack the Future hackathon.", "prize": "100000"},
    {"source": "unstop", "source_id": "unstop_200", "source_url": "https://unstop.com/hackathons/sih-2026",
     "title": "Smart India Hackathon 2026", "organizer": "Government of India", "start_date": "2026-01-27",
     "location": "Delhi", "registration_link": "https://sih.gov.in/register",
     "description": "National level hackathon.", "prize": "100000"},
    {"source": "devfolio", "source_id": "devfolio_201", "source_url": "https://devfolio.co/sih-2026",
     "title": "SIH - Smart India Hackathon", "organizer": "Government of India", "start_date": "2026-01-28",
     "location": "New Delhi", "registration_link": "https://sih.gov.in/register/",
     "description": "Smart India Hackathon 2026 - the biggest national hackathon with problem statements from ministries and industry.", "prize": "75000"},
    {"source": "mlh", "source_id": "mlh_300", "source_url": "https://mlh.io/hackfest-2025",
     "title": "HackFest 2025", "organizer": "TechClub", "start_date": "2025-03-15",
     "location": "Bengaluru", "registration_link": "https://hackfest.io/2025",
     "description": "HackFest 2025 edition.", "prize": "20000"},
    {"source": "unstop", "source_id": "unstop_301", "source_url": "https://unstop.com/hackfest-2026",
     "title": "HackFest 2026", "organizer": "TechClub", "start_date": "2026-03-14",
     "location": "Bengaluru", "registration_link": "https://hackfest.io/2026",
     "description": "HackFest 2026 edition.", "prize": "30000"},
    {"source": "meetup", "source_id": "meetup_400", "source_url": "https://meetup.com/pyhyd/event-400",
     "title": "Python Hyderabad Monthly Meetup", "organizer": "PyHyd", "start_date": "2026-11-08",
     "location": "Hyderabad", "registration_link": "https://meetup.com/pyhyd/event-400",
     "description": "Monthly talks and networking.", "prize": ""},
]

# ---------------- NORMALIZATION ----------------
def normalize_link(url):
    """Normalize a URL for equality while retaining meaningful query parameters."""
    if not url:
        return ""
    raw = url.strip()
    if not raw:
        return ""
    p = urlparse(raw if "://" in raw else "https://" + raw)
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    # Default ports do not change the resource identity. Malformed ports
    # should not crash an audit; leave them for the structural URL checker.
    try:
        port = p.port
    except ValueError:
        port = None
    if port and not ((p.scheme.lower() == "https" and port == 443) or
                     (p.scheme.lower() == "http" and port == 80)):
        host = f"{host}:{port}"
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in
             {"fbclid", "gclid", "ref", "source"}]
    query.sort()
    path = re.sub(r"/+", "/", p.path or "").rstrip("/")
    q = ("?" + urlencode(query)) if query else ""
    return f"{host}{path}{q}"


def trailing_id(norm_link):
    """Numeric ID at the end of a URL path (aggregators reuse the source site's ID), e.g. ...-1752595"""
    m = re.search(r"(\d{6,})$", (norm_link or "").split("?")[0])
    return m.group(1) if m else ""


def normalize_title(title):
    t = re.sub(r"[^a-z0-9 ]", " ", (title or "").lower())
    t = re.sub(r"\b(19|20)\d{2}\b", " ", t)  # drop years
    t = re.sub(r"\bmachine learning\b", "ml", t)
    words = [TITLE_ALIASES.get(w, w) for w in t.split()]
    return " ".join(words)


TITLE_GENERIC_WORDS = {
    "event", "hackathon", "hackathons", "workshop", "workshops", "contest", "competition",
    "challenge", "summit", "conference", "meetup", "meet", "bootcamp", "series",
    "online", "national", "international", "annual", "the", "and", "for", "of", "in",
}

def title_similarity(a, b):
    """Score title similarity without letting generic shared words dominate."""
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return 0
    if na == nb:
        return 100
    informative_a = {w for w in na.split() if w not in TITLE_GENERIC_WORDS}
    informative_b = {w for w in nb.split() if w not in TITLE_GENERIC_WORDS}
    if informative_a and informative_b and not (informative_a & informative_b):
        return 0
    return fuzz.token_sort_ratio(na, nb)

def normalize_location(loc):
    l = re.sub(r"[^a-z ]", " ", (loc or "").lower())
    l = re.sub(r"\s+", " ", l).strip()
    return LOCATION_ALIASES.get(l, l)


def same_location(a, b):
    """True if normalized locations match, or share a meaningful word (e.g. 'NIT Hamirpur' vs 'Hamirpur, India')."""
    na, nb = normalize_location(a), normalize_location(b)
    # Missing locations are unknown, not evidence that two events share a venue.
    if not na or not nb:
        return False
    if na == nb:
        return True
    ta = {w for w in na.split() if w not in LOCATION_STOPWORDS}
    tb = {w for w in nb.split() if w not in LOCATION_STOPWORDS}
    return bool(ta and tb and ta & tb)


def parse_date(s):
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def title_year(title):
    m = re.search(r"\b((?:19|20)\d{2})\b", title or "")
    return m.group(1) if m else None

# ---------------- MATCHING ----------------
def compare(a, b):
    """Return (label, reason, score). label in duplicate / uncertain / not_duplicate"""
    # Registration pages are often reused for subsequent editions.
    ya, yb = title_year(a.get("title", "")), title_year(b.get("title", ""))
    da, db = parse_date(a.get("start_date", "")), parse_date(b.get("start_date", ""))
    if (ya and yb and ya != yb) or (da and db and abs((da - db).days) > UNCERTAIN_DATE_DAYS):
        return "not_duplicate", "conflicting edition dates or years", 0
    # Level 1: exact registration link
    la, lb = normalize_link(a["registration_link"]), normalize_link(b["registration_link"])
    if la and la == lb:
        return "duplicate", "L1 exact registration_link", 100

    # Level 1b: same numeric source ID in both URLs (+ similar title) -> same listing re-published
    ida, idb = trailing_id(la), trailing_id(lb)
    if (ida and ida == idb and la.split('/')[0] == lb.split('/')[0]
            and title_similarity(a["title"], b["title"]) >= 60):
        return "duplicate", "L1b same source ID in URL", 100

    # Level 2: fuzzy
    score = title_similarity(a["title"], b["title"])
    da, db = parse_date(a["start_date"]), parse_date(b["start_date"])
    date_ok = da is not None and db is not None and abs((da - db).days) <= MAX_DATE_DIFF_DAYS
    loc_ok = same_location(a["location"], b["location"])

    # organizer check: clearly different organizers -> different events
    oa_raw = re.sub(r"[^a-z0-9 ]", " ", (a.get("organizer") or "").lower()).strip()
    ob_raw = re.sub(r"[^a-z0-9 ]", " ", (b.get("organizer") or "").lower()).strip()
    # Generic suffixes (College, Club, Organization, etc.) should not make
    # unrelated organizers look similar merely because they share a suffix.
    oa = " ".join(w for w in oa_raw.split() if w not in ORG_STOPWORDS)
    ob = " ".join(w for w in ob_raw.split() if w not in ORG_STOPWORDS)
    if oa and ob and fuzz.token_sort_ratio(oa, ob) < ORG_MIN_SIM:
        return "not_duplicate", "organizer mismatch", score

    date_close = da is not None and db is not None and abs((da - db).days) <= UNCERTAIN_DATE_DAYS

    ya, yb = title_year(a["title"]), title_year(b["title"])
    if ya and yb and ya != yb:
        return "not_duplicate", "different year in title", score

    if score >= DUP_THRESHOLD and date_ok and loc_ok:
        return "duplicate", f"L2 title={score:.0f} date_ok loc_ok", score
    if score >= UNCERTAIN_THRESHOLD and date_close:
        return "uncertain", f"title={score:.0f} date_ok={date_ok} loc_ok={loc_ok}", score
    return "not_duplicate", f"title={score:.0f} date_ok={date_ok} loc_ok={loc_ok}", score

# ---------------- CLUSTERING (union-find) ----------------
def _candidate_pairs(events):
    """Generate only pairs that can match under the rules, avoiding a full N² scan.

    Fuzzy duplicate/uncertain decisions require dates within seven days. Exact
    normalized registration links and shared numeric URL IDs remain candidates
    even when dates are missing or far apart.
    """
    pairs = set()
    by_link = defaultdict(list)
    by_url_id = defaultdict(list)
    dated = []
    for i, event in enumerate(events):
        norm = normalize_link(event.get("registration_link", ""))
        if norm:
            by_link[norm].append(i)
            url_id = trailing_id(norm)
            if url_id:
                by_url_id[url_id].append(i)
        dt = parse_date(event.get("start_date", ""))
        if dt:
            dated.append((dt, i))

    for buckets in (by_link, by_url_id):
        for indices in buckets.values():
            for pos, i in enumerate(indices):
                for j in indices[pos + 1:]:
                    pairs.add((min(i, j), max(i, j)))

    # Sort by date; scan forward only through the maximum uncertain date range.
    dated.sort()
    for pos, (dt, i) in enumerate(dated):
        nxt = pos + 1
        while nxt < len(dated) and (dated[nxt][0] - dt).days <= UNCERTAIN_DATE_DAYS:
            j = dated[nxt][1]
            pairs.add((min(i, j), max(i, j)))
            nxt += 1
    return sorted(pairs)


def cluster(events):
    parent = list(range(len(events)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    uncertain = []
    for i, j in _candidate_pairs(events):
        label, reason, score = compare(events[i], events[j])
        if label == "duplicate":
            # Prevent a sparse bridge record from joining conflicting editions.
            left = [k for k in range(len(events)) if find(k) == find(i)]
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
    return compare(map_record(a, 0), map_record(b, 1))[0] == "duplicate"

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
