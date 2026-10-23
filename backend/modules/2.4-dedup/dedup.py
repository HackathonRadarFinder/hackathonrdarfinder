
import csv
import json
import re
from datetime import date, datetime
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse


def normalize_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def normalize_link(url):
    """Normalize URLs and remove common tracking parameters."""
    if not url:
        return ""

    raw = str(url).strip()
    if not raw:
        return ""

    try:
        parsed = urlparse(raw if "://" in raw else "https://" + raw)
        hostname = parsed.hostname
    except ValueError:
        hostname = None
        parsed = None

    if not hostname or parsed is None:
        return raw.rstrip("/").lower()

    hostname = hostname.lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]

    path = parsed.path.rstrip("/")
    ignored = {
        "fbclid", "gclid", "dclid", "msclkid",
        "ref", "source", "campaign"
    }

    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
        and key.lower() not in ignored
    ]

    result = hostname + path
    if query:
        result += "?" + urlencode(sorted(query))
    return result


def similarity(text1, text2):
    a = normalize_text(text1)
    b = normalize_text(text2)

    if not a or not b:
        return 0.0

    sequence_score = SequenceMatcher(None, a, b).ratio()
    words_a = set(re.findall(r"\b\w+\b", a))
    words_b = set(re.findall(r"\b\w+\b", b))

    token_score = (
        len(words_a & words_b) / len(words_a | words_b)
        if words_a or words_b else 0.0
    )
    return max(sequence_score, token_score) * 100


def parse_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    try:
        return datetime.fromisoformat(
            text.replace("Z", "+00:00")
        ).date()
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def dates_match(date1, date2, tolerance_days=2):
    first, second = parse_date(date1), parse_date(date2)
    return (
        first is not None
        and second is not None
        and abs((first - second).days) <= tolerance_days
    )


def same_location(location1, location2):
    first = normalize_text(location1)
    second = normalize_text(location2)
    return bool(first and second and first == second)


def _title_key(text):
    synonyms = {
        "expo": "exhibition",
        "exposition": "exhibition",
        "ml": "machine learning",
    }
    words = re.findall(r"\b\w+\b", normalize_text(text))
    return " ".join(synonyms.get(word, word) for word in words)

def _different_explicit_year(title1, title2):
    years1 = set(re.findall(r"\b20\d{2}\b", normalize_text(title1)))
    years2 = set(re.findall(r"\b20\d{2}\b", normalize_text(title2)))
    return bool(years1 and years2 and years1 != years2)


def are_duplicates(event1, event2, title_threshold=80):
    """Conservatively determine whether two events are duplicates."""
    link1 = normalize_link(event1.get("registration_link"))
    link2 = normalize_link(event2.get("registration_link"))

    if link1 and link2 and link1 == link2:
        return True

    title1 = normalize_text(event1.get("title"))
    title2 = normalize_text(event2.get("title"))
    org1 = normalize_text(event1.get("organizer"))
    org2 = normalize_text(event2.get("organizer"))
    loc1 = normalize_text(event1.get("location"))
    loc2 = normalize_text(event2.get("location"))

    if not all((title1, title2, org1, org2, loc1, loc2)):
        return False

    if _different_explicit_year(title1, title2):
        return False

    return (
        similarity(_title_key(title1), _title_key(title2))
        >= title_threshold
        and org1 == org2
        and same_location(loc1, loc2)
        and dates_match(
            event1.get("start_date"),
            event2.get("start_date")
        )
    )


def compare(event1, event2):
    """Return (decision, reason) for a pair of event records."""
    link1 = normalize_link(event1.get("registration_link"))
    link2 = normalize_link(event2.get("registration_link"))

    if link1 and link2 and link1 == link2:
        return "duplicate", "Same normalized registration link"

    title1 = normalize_text(event1.get("title"))
    title2 = normalize_text(event2.get("title"))
    org1 = normalize_text(event1.get("organizer"))
    org2 = normalize_text(event2.get("organizer"))

    if not title1 or not title2:
        return "not_duplicate", "Missing title"

    if _different_explicit_year(title1, title2):
        return "not_duplicate", "Different event years"

    if org1 and org2 and org1 != org2:
        return "not_duplicate", "Different organizers"

    if similarity(_title_key(title1), _title_key(title2)) < 80:
        return "not_duplicate", "Titles are insufficiently similar"

    if not same_location(
        event1.get("location"), event2.get("location")
    ):
        return "not_duplicate", "Locations are missing or different"

    if not dates_match(
        event1.get("start_date"), event2.get("start_date")
    ):
        return "not_duplicate", "Dates do not match"

    if not org1 or not org2:
        return "not_duplicate", "Organizer evidence is missing"

    return "duplicate", "Similar title, organizer, location and date"


def _date_only(value):
    parsed = parse_date(value)
    return parsed.isoformat() if parsed else str(value or "").strip()


def map_record(raw, index=0):
    """Map Module 2.3/API fields into the canonical event schema."""
    raw = dict(raw)

    title = raw.get("title") or raw.get("event_name") or raw.get("name") or ""
    source = raw.get("source") or raw.get("source_name") or ""
    source_id = raw.get("source_id") or raw.get("event_id") or ""

    tags = raw.get("tags") or []
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    if not isinstance(tags, list):
        tags = []
    unique_tags = list(dict.fromkeys(tag for tag in tags if tag))

    record = dict(raw)
    record.update({
        "title": str(title).strip(),
        "organizer": raw.get("organizer") or raw.get("organizer_name") or "",
        "start_date": _date_only(raw.get("start_date")),
        "end_date": _date_only(raw.get("end_date")),
        "registration_deadline": _date_only(
            raw.get("registration_deadline") or raw.get("deadline")
        ),
        "location": raw.get("location") or raw.get("venue") or "",
        "registration_link": (
            raw.get("registration_link")
            or raw.get("registration_url")
            or raw.get("apply_url")
            or ""
        ),
        "source": source,
        "source_name": raw.get("source_name") or source,
        "source_id": source_id,
        "source_url": raw.get("source_url") or raw.get("url") or "",
        "mode": raw.get("mode") or "",
        "status": raw.get("status") or "",
        "tags": unique_tags,
        "description": raw.get("description") or "",
        "prize": raw.get("prize") or "",
        "_input_index": index,
    })
    return record


def _registration_key(event):
    return normalize_link(event.get("registration_link"))


def cluster(events):
    """Group duplicates and return groups plus uncertain candidate pairs."""
    groups = []
    link_groups = {}

    for event in events:
        link = _registration_key(event)
        if link:
            if link in link_groups:
                link_groups[link].append(event)
            else:
                group = [event]
                link_groups[link] = group
                groups.append(group)
        else:
            groups.append([event])

    buckets = {}
    for group in groups:
        event = group[0]
        key = (
            normalize_text(event.get("organizer")),
            _date_only(event.get("start_date")),
            normalize_text(event.get("location")),
        )
        buckets.setdefault(key, []).append(group)

    final_groups = []
    uncertain = []

    for bucket in buckets.values():
        bucket_groups = []

        for group in bucket:
            event = group[0]
            matched = False

            for existing_group in bucket_groups:
                decision, reason = compare(existing_group[0], event)

                if decision == "duplicate":
                    existing_group.extend(group)
                    matched = True
                    break

                if similarity(
                    event.get("title"),
                    existing_group[0].get("title")
                ) >= 65:
                    uncertain.append({
                        "event_a": existing_group[0],
                        "event_b": event,
                        "reason": reason,
                    })

            if not matched:
                bucket_groups.append(group)

        final_groups.extend(bucket_groups)

    return final_groups, uncertain


def merge_group(group, canonical_id):
    """Merge events and preserve source provenance and unique tags."""
    if not group:
        raise ValueError("Cannot merge an empty event group")

    canonical = dict(group[0])
    provenance = []
    tags = []

    for event in group:
        event_source = event.get("source") or event.get("source_name") or ""
        event_id = event.get("source_id") or ""
        event_url = event.get("source_url") or ""

        if event_source or event_id or event_url:
            item = {
                "source": event_source,
                "source_id": event_id,
                "url": event_url,
            }
            if item not in provenance:
                provenance.append(item)

        event_tags = event.get("tags", []) or []
        if isinstance(event_tags, str):
            event_tags = [tag.strip() for tag in event_tags.split(",")]

        for tag in event_tags:
            if tag and tag not in tags:
                tags.append(tag)

        for key, value in event.items():
            if canonical.get(key) in ("", None, []):
                if value not in ("", None, []):
                    canonical[key] = value

    canonical["canonical_event_id"] = canonical_id
    canonical["provenance"] = provenance
    canonical["tags"] = tags
    canonical["source_id"] = canonical.get("source_id", "")
    canonical["source_name"] = (
        canonical.get("source_name") or canonical.get("source", "")
    )
    return canonical


def load(path):
    """Load JSON lists, nested API wrappers, or CSV event exports."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    if file_path.suffix.lower() == ".csv":
        with file_path.open(
            "r", encoding="utf-8-sig", newline=""
        ) as file:
            rows = list(csv.DictReader(file))
    else:
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        # Unwrap common API response shapes, including data.results.
        while isinstance(data, dict):
            found = False
            for key in ("events", "valid", "expired", "results", "data"):
                value = data.get(key)
                if isinstance(value, list):
                    data = value
                    found = True
                    break
                if isinstance(value, dict):
                    data = value
                    found = True
                    break
            if not found:
                raise ValueError(
                    "Expected a JSON list or API wrapper containing a list"
                )

        if not isinstance(data, list):
            raise ValueError(
                "Expected a JSON list or API wrapper containing a list"
            )
        rows = data

    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue

        event = row.copy()
        if not event.get("title") and event.get("event_name"):
            event["title"] = event["event_name"]
        normalized.append(event)

    return normalized


def find_duplicates(events):
    """Return pairs of indices representing duplicate events."""
    pairs = []
    for i in range(len(events)):
        for j in range(i + 1, len(events)):
            if are_duplicates(events[i], events[j]):
                pairs.append((i, j))
    return pairs


SAMPLE = [
    {
        "title": "AI Hackathon",
        "organizer": "Tech Club",
        "start_date": "2026-10-20",
        "location": "Online",
        "registration_link": "https://sample.test/register/1",
        "source": "Unstop",
        "source_id": "s1",
        "tags": ["AI"],
    },
    {
        "title": "AI Hackathon",
        "organizer": "Tech Club",
        "start_date": "2026-10-20",
        "location": "Online",
        "registration_link": "https://sample.test/register/1",
        "source": "Devfolio",
        "source_id": "s2",
        "tags": ["AI", "Python"],
    },
    {
        "title": "Web Contest",
        "organizer": "Coding Club",
        "start_date": "2026-11-01",
        "location": "Chennai",
        "registration_link": "https://sample.test/register/2",
    },
    {
        "title": "Web Contest",
        "organizer": "Coding Club",
        "start_date": "2026-11-01",
        "location": "Chennai",
        "registration_link": "https://sample.test/register/2",
    },
    {
        "title": "Robotics Workshop",
        "organizer": "Engineering Society",
        "start_date": "2026-11-05",
        "location": "Pune",
        "registration_link": "https://sample.test/register/3",
    },
    {
        "title": "Design Challenge",
        "organizer": "Design Club",
        "start_date": "2026-11-12",
        "location": "Online",
        "registration_link": "https://sample.test/register/4",
    },
    {
        "title": "Cybersecurity Talk",
        "organizer": "Security Club",
        "start_date": "2026-11-18",
        "location": "Delhi",
        "registration_link": "https://sample.test/register/5",
    },
]
