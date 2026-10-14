import re
from datetime import date, datetime
from difflib import SequenceMatcher
from urllib.parse import urlparse, urlunparse


def normalize_text(value):
    """Normalize text before comparing."""
    if value is None:
        return ""

    text = str(value).strip().lower()
    return re.sub(r"\s+", " ", text)


def normalize_link(url):
    """Normalize registration links for comparison."""
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
    """Calculate title similarity as a percentage."""
    a = normalize_text(text1)
    b = normalize_text(text2)

    if not a or not b:
        return 0.0

    sequence_score = SequenceMatcher(None, a, b).ratio()

    words_a = set(re.findall(r"\b\w+\b", a))
    words_b = set(re.findall(r"\b\w+\b", b))

    if not words_a or not words_b:
        token_score = 0.0
    else:
        token_score = len(words_a & words_b) / len(words_a | words_b)

    return max(sequence_score, token_score) * 100


def dates_match(date1, date2, tolerance_days=2):
    """Check whether dates differ by at most two days."""

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
    Identify duplicate event records.

    Expected keys:
    registration_link, title, organizer, start_date, location.
    """

    link1 = normalize_link(event1.get("registration_link"))
    link2 = normalize_link(event2.get("registration_link"))

    # Rule 1: Same non-empty registration link.
    if link1 and link2 and link1 == link2:
        return True

    title1 = normalize_text(event1.get("title"))
    title2 = normalize_text(event2.get("title"))
    organizer1 = normalize_text(event1.get("organizer"))
    organizer2 = normalize_text(event2.get("organizer"))
    location1 = normalize_text(event1.get("location"))
    location2 = normalize_text(event2.get("location"))

    # Missing required details should not produce a fuzzy match.
    if not all((
        title1, title2,
        organizer1, organizer2,
        location1, location2
    )):
        return False

    # Compare event titles using character and word similarity.
    title_score = similarity(title1, title2)

    same_organizer = organizer1 == organizer2
    same_location = location1 == location2
    same_date = dates_match(
        event1.get("start_date"),
        event2.get("start_date"),
        tolerance_days=2
    )

    # Rule 2: Similar title plus matching event details.
    return (
        title_score > title_threshold
        and same_organizer
        and same_date
        and same_location
    )


def find_duplicates(events):
    """Return pairs of indices representing duplicate events."""
    duplicate_pairs = []

    for i in range(len(events)):
        for j in range(i + 1, len(events)):
            if are_duplicates(events[i], events[j]):
                duplicate_pairs.append((i, j))

    return duplicate_pairs
