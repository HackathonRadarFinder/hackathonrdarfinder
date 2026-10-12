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
from itertools import combinations
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

# ---------------- INPUT FORMAT (edit this when Shivam shares his format) ----------------
# left side = the names this script uses; right side = names that may appear in the input file.
# If Shivam's output uses a different name, just add it to the list.
FIELD_MAP = {
    "source":            ["source", "site", "platform"],
    "source_id":         ["source_id", "id", "event_id"],
    "source_url":        ["source_url", "url", "page_url", "event_url"],
    "title":             ["title", "name", "event_name"],
    "organizer":         ["organizer", "organiser", "host", "organized_by"],
    "start_date":        ["start_date", "date_start", "startdate", "date"],
    "location":          ["location", "city", "venue"],
    "registration_link": ["registration_link", "register_url", "registration_url", "apply_link"],
    "description":       ["description", "desc", "about"],
    "prize":             ["prize", "prize_pool", "prizes"],
}

DATE_FORMATS = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y"]


def to_iso(value):
    """Convert common date formats to YYYY-MM-DD (empty string if it can't be read)."""
    value = (value or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def map_record(raw, index):
    """Turn one raw input record into the field names used by this script."""
    lower = {str(k).strip().lower(): v for k, v in raw.items()}
    rec = {}
    for field, names in FIELD_MAP.items():
        rec[field] = ""
        for n in names:
            if lower.get(n) not in (None, ""):
                rec[field] = str(lower[n]).strip()
                break
    rec["start_date"] = to_iso(rec["start_date"])
    rec["source"] = rec["source"] or "unknown"
    rec["source_id"] = rec["source_id"] or f"row_{index}"
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
    if not url:
        return ""
    p = urlparse(url.strip().lower())
    scheme_less_host = p.netloc.replace("www.", "")
    query = [(k, v) for k, v in parse_qsl(p.query) if not k.startswith("utm_")]
    path = p.path.rstrip("/")
    q = ("?" + urlencode(query)) if query else ""
    return f"{scheme_less_host}{path}{q}"


def trailing_id(norm_link):
    """Numeric ID at the end of a URL path (aggregators reuse the source site's ID), e.g. ...-1752595"""
    m = re.search(r"(\d{6,})$", (norm_link or "").split("?")[0])
    return m.group(1) if m else ""


def normalize_title(title):
    t = re.sub(r"[^a-z0-9 ]", " ", (title or "").lower())
    t = re.sub(r"\b(19|20)\d{2}\b", " ", t)  # drop years
    words = [TITLE_ALIASES.get(w, w) for w in t.split()]
    return " ".join(words)


def normalize_location(loc):
    l = re.sub(r"[^a-z ]", " ", (loc or "").lower())
    l = re.sub(r"\s+", " ", l).strip()
    return LOCATION_ALIASES.get(l, l)


def same_location(a, b):
    """True if normalized locations match, or share a meaningful word (e.g. 'NIT Hamirpur' vs 'Hamirpur, India')."""
    na, nb = normalize_location(a), normalize_location(b)
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
    # Level 1: exact registration link
    la, lb = normalize_link(a["registration_link"]), normalize_link(b["registration_link"])
    if la and la == lb:
        return "duplicate", "L1 exact registration_link", 100

    # Level 1b: same numeric source ID in both URLs (+ similar title) -> same listing re-published
    ida, idb = trailing_id(la), trailing_id(lb)
    if ida and ida == idb and fuzz.token_set_ratio(normalize_title(a["title"]), normalize_title(b["title"])) >= 60:
        return "duplicate", "L1b same source ID in URL", 100

    # Level 2: fuzzy
    score = fuzz.token_set_ratio(normalize_title(a["title"]), normalize_title(b["title"]))
    da, db = parse_date(a["start_date"]), parse_date(b["start_date"])
    date_ok = da is not None and db is not None and abs((da - db).days) <= MAX_DATE_DIFF_DAYS
    loc_ok = same_location(a["location"], b["location"])

    # organizer check: clearly different organizers -> different events
    oa = re.sub(r"[^a-z0-9 ]", " ", (a.get("organizer") or "").lower()).strip()
    ob = re.sub(r"[^a-z0-9 ]", " ", (b.get("organizer") or "").lower()).strip()
    if oa and ob and fuzz.token_set_ratio(oa, ob) < ORG_MIN_SIM:
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
def cluster(events):
    parent = list(range(len(events)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    uncertain = []
    for i, j in combinations(range(len(events)), 2):
        label, reason, score = compare(events[i], events[j])
        if label == "duplicate":
            parent[find(i)] = find(j)
        elif label == "uncertain":
            uncertain.append({"id_a": events[i]["source_id"], "id_b": events[j]["source_id"],
                              "title_a": events[i]["title"], "title_b": events[j]["title"],
                              "reason": reason})
    groups = {}
    for i in range(len(events)):
        groups.setdefault(find(i), []).append(events[i])
    return list(groups.values()), uncertain

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
    return {
        "canonical_event_id": canonical_id,
        "title": best_title,
        "organizer": first("organizer"),
        "start_date": first("start_date"),
        "location": first("location"),
        "registration_link": first("registration_link"),
        "description": best_desc,
        "prize": best_prize,
        "source_ids": [e["source_id"] for e in group],
        "provenance": [
            {"source": e["source"], "source_id": e["source_id"], "url": e["source_url"],
             "seen_on": date.today().isoformat()} for e in group
        ],
    }

# ---------------- MAIN ----------------
def load(path):
    if path.lower().endswith(".json"):
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    else:
        with open(path, newline="", encoding="utf-8") as f:
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
