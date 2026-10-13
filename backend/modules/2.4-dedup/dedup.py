
import re
from difflib import SequenceMatcher
from urllib.parse import urlparse, urlunparse


def normalize_text(value):
    """Normalize text before comparing."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def normalize_link(url):
    """Normalize a registration URL for exact matching."""
    if not url:
        return ""

    url = str(url).strip()
    parsed = urlparse(url)

    if not parsed.scheme or not parsed.netloc:
        return url.rstrip("/").lower()

    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path.rstrip("/"),
        "",
        "",
        ""
    ))


def similarity(text1, text2):
    """Return title similarity from 0 to 100."""
    a = normalize_text(text1)
    b = normalize_text(text2)

    if not a or not b:
        return 0.0

    return SequenceMatcher(None, a, b).ratio() * 100


def dates_match(date1, date2, tolerance_days=2):
    """Compare dates allowing a difference of up to 2 days."""
    from datetime import date, datetime

    def parse_date(value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value

        value = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value[:10], fmt).date()
            except ValueError:
                continue
        return None

    d1 = parse_date(date1)
    d2 = parse_date(date2)

    if d1 is None or d2 is None:
        return False

    return abs((d1 - d2).days) <= tolerance_days


def are_duplicates(event1, event2, title_threshold=80):
    """
    Compare two event dictionaries.
    Expected keys: registration_link, title, organizer,
    start_date, location.
    """
    link1 = normalize_link(event1.get("registration_link"))
    link2 = normalize_link(event2.get("registration_link"))

    # Exact registration link match
    if link1 and link2 and link1 == link2:
        return True

    title_score = similarity(
        event1.get("title"),
        event2.get("title")
    )

    organizer1 = normalize_text(event1.get("organizer"))
    organizer2 = normalize_text(event2.get("organizer"))

    same_organizer = bool(
        organizer1 and organizer2 and organizer1 == organizer2
    )

    same_date = dates_match(
        event1.get("start_date"),
        event2.get("start_date"),
        tolerance_days=2
    )

    location1 = normalize_text(event1.get("location"))
    location2 = normalize_text(event2.get("location"))
    same_location = bool(
        location1 and location2 and location1 == location2
    )

    # Fuzzy title + supporting event details
    return (
        title_score > title_threshold
        and same_organizer
        and same_date
        and same_location
    )


def find_duplicates(events):
    """Return pairs of event indices that appear duplicated."""
    duplicate_pairs = []

    for i in range(len(events)):
        for j in range(i + 1, len(events)):
            if are_duplicates(events[i], events[j]):
                duplicate_pairs.append((i, j))

    return duplicate_pairs
