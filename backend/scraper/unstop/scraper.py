"""Unstop hackathon scraper (SCR-002).

Source:    https://unstop.com/hackathons  (public listing)
Data from: Unstop's public JSON endpoint /api/public/opportunity/search-result, the same one the
           listing page itself calls. robots.txt explicitly allows /api/public/* and /hackathons/.

Compliance (checked 2026-10-08): robots.txt is fetched and obeyed on every run (wildcard-aware),
Terms of Use contain no scraping prohibition, identifiable User-Agent, 1-2 s between requests,
no login, no CAPTCHA/anti-bot bypass. A 401/403/429 stops the run immediately.

Usage:
    python backend/scraper/unstop/scraper.py            # prints count + first 5 records
    from backend.scraper.unstop import scrape; records = scrape(limit=30)

No API keys or secrets are used. Optional env var: UNSTOP_SCRAPER_USER_AGENT.
"""
from __future__ import annotations

import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Optional
from urllib.parse import urlsplit

import requests

SOURCE = "Unstop"
BASE_URL = "https://unstop.com"
API_URL = f"{BASE_URL}/api/public/opportunity/search-result"
ROBOTS_URL = f"{BASE_URL}/robots.txt"
USER_AGENT = os.environ.get(
    "UNSTOP_SCRAPER_USER_AGENT",
    "HackathonRadarBot/1.0 (+https://github.com/HackathonRadarFinder; student hackathon aggregator)",
)

PER_PAGE = 15
DEFAULT_LIMIT = 30  # max records per run unless scrape(limit=...) says otherwise
MIN_DELAY, MAX_DELAY = 1.0, 2.0  # polite gap between requests (seconds)
MAX_ATTEMPTS = 3
BACKOFF_BASE = 2.0  # 2 s, then 4 s
TIMEOUT = 20

BLOCK_STATUSES = {401, 403, 429}  # access refused: never retried, never bypassed

log = logging.getLogger("unstop_scraper")


class _Blocked(Exception):
    """Unstop refused access (401/403/429)."""


# --------------------------------------------------------------------------- robots.txt
def _pattern_to_regex(pattern: str) -> "re.Pattern[str]":
    """robots.txt path pattern -> regex ('*' = any chars, trailing '$' = end of URL)."""
    anchored = pattern.endswith("$")
    body = re.escape(pattern[:-1] if anchored else pattern).replace(r"\*", ".*")
    return re.compile("^" + body + ("$" if anchored else ""))


def parse_robots(text: str, user_agent: str = USER_AGENT) -> list[tuple[bool, "re.Pattern[str]", int]]:
    """Rules (allow?, regex, length) for our UA, falling back to the '*' group.

    Python's urllib.robotparser ignores '*' wildcards, which Unstop's robots.txt uses, so this is
    a small RFC 9309-style implementation: the longest matching rule wins, Allow wins a tie.
    """
    token = user_agent.split("/")[0].strip().lower()
    groups: dict[str, list[tuple[bool, str]]] = {}
    current: list[str] = []
    last_was_agent = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        field, value = (p.strip() for p in line.split(":", 1))
        field = field.lower()
        if field == "user-agent":
            if not last_was_agent:
                current = []
            current.append(value.lower())
            groups.setdefault(value.lower(), [])
            last_was_agent = True
        elif field in ("allow", "disallow"):
            last_was_agent = False
            if value:  # an empty Disallow means "allow all" - nothing to record
                for agent in current:
                    groups[agent].append((field == "allow", value))
        else:
            last_was_agent = False
    chosen = groups.get(token) if token in groups else groups.get("*", [])
    return [(allow, _pattern_to_regex(p), len(p)) for allow, p in chosen]


def is_allowed(rules: list, path: str) -> bool:
    matches = [(length, allow) for allow, rx, length in rules if rx.match(path)]
    if not matches:
        return True
    best = max(length for length, _ in matches)
    return any(allow for length, allow in matches if length == best)  # Allow wins ties


def check_robots(session: requests.Session) -> bool:
    """True if our User-Agent may fetch the listing API. Unverifiable robots.txt -> False."""
    try:
        resp = session.get(ROBOTS_URL, timeout=TIMEOUT)
    except requests.RequestException as exc:
        log.error("robots.txt unreachable (%s); not scraping", exc)
        return False
    if resp.status_code in BLOCK_STATUSES or resp.status_code >= 500:
        log.error("robots.txt returned HTTP %s; cannot verify, not scraping", resp.status_code)
        return False
    if resp.status_code != 200:
        log.info("no robots.txt (HTTP %s): allowed", resp.status_code)
        return True
    rules = parse_robots(resp.text)
    path = urlsplit(API_URL).path
    allowed = is_allowed(rules, path)
    log.info("robots.txt check path=%s allowed=%s", path, allowed)
    return allowed


# --------------------------------------------------------------------------- HTTP
def _get_page(session: requests.Session, page: int) -> dict[str, Any]:
    """Fetch one listing page with retry/backoff on temporary failures only."""
    params = {"opportunity": "hackathons", "oppstatus": "open", "per_page": PER_PAGE, "page": page}
    last_error: Optional[Exception] = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = session.get(API_URL, params=params, timeout=TIMEOUT)
            if resp.status_code in BLOCK_STATUSES:
                raise _Blocked(f"HTTP {resp.status_code}")
            if resp.status_code >= 500 or resp.status_code == 408:
                raise requests.HTTPError(f"HTTP {resp.status_code}")
            resp.raise_for_status()  # other 4xx: permanent
            return resp.json()
        except _Blocked:
            raise
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_error = exc
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code < 500:
                raise  # permanent 4xx, do not retry
            last_error = exc
        except ValueError as exc:  # invalid JSON body
            last_error = exc
        if attempt < MAX_ATTEMPTS:
            delay = BACKOFF_BASE * 2 ** (attempt - 1)
            log.warning("page %d attempt %d/%d failed: %s; retrying in %.0fs", page, attempt, MAX_ATTEMPTS, last_error, delay)
            time.sleep(delay)
    raise RuntimeError(f"page {page} failed after {MAX_ATTEMPTS} attempts: {last_error}")


# --------------------------------------------------------------------------- parsing helpers
class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in ("br", "p", "li", "div", "h1", "h2", "h3", "h4"):
            self.parts.append(" ")


def html_to_text(value: Any) -> str:
    if not value or not isinstance(value, str):
        return ""
    parser = _TextExtractor()
    try:
        parser.feed(value)
        parser.close()
    except Exception:  # malformed HTML must never break a record
        return re.sub(r"<[^>]+>", " ", value).strip()
    return re.sub(r"\s+", " ", "".join(parser.parts)).strip()


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", value).strip() if isinstance(value, str) else ""


def _iso(value: Any) -> Optional[str]:
    """Return an ISO-8601 string, or None when missing/unparseable."""
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return None


_CURRENCY = {"fa-rupee": "₹", "fa-inr": "₹", "fa-dollar": "$", "fa-usd": "$", "fa-euro": "€", "fa-eur": "€"}


def format_prize(prizes: Any) -> str:
    """e.g. '₹5,000 total cash (3 prizes) + certificates'. Empty string when none."""
    if not isinstance(prizes, list) or not prizes:
        return ""
    cash: dict[str, float] = {}
    certificates = False
    others: list[str] = []
    for p in prizes:
        if not isinstance(p, dict):
            continue
        amount = p.get("cash")
        if isinstance(amount, (int, float)) and amount > 0:
            symbol = _CURRENCY.get(p.get("currency") or "", p.get("currencyCode") or "")
            cash[symbol] = cash.get(symbol, 0) + amount
        certificates = certificates or bool(p.get("certificate"))
        other = _clean(p.get("others"))
        if other and other not in others:
            others.append(other)
    parts = [f"{sym}{total:,.0f} total cash" if sym else f"{total:,.0f} total cash" for sym, total in cash.items()]
    if not parts and others:  # no cash: fall back to the first free-text prize (e.g. "Internship offer")
        parts.append(others[0])
    if certificates:
        parts.append("certificates")
    return " + ".join(parts)


def _location_and_mode(item: dict) -> tuple[str, str]:
    region = _clean(item.get("region")).lower()
    mode = {"online": "Online", "offline": "Offline", "hybrid": "Hybrid"}.get(region, "")
    place: list[str] = []
    addr = item.get("address_with_country_logo")
    if isinstance(addr, dict):
        country = addr.get("country")
        for part in (addr.get("city"), addr.get("state"), country.get("name") if isinstance(country, dict) else None):
            if _clean(part) and _clean(part) not in place:
                place.append(_clean(part))
    location = ", ".join(place)
    if not location and mode == "Online":
        location = "Online"
    return location, mode


def normalise(item: Any, scraped_at: str) -> Optional[dict[str, Any]]:
    """Map one Unstop opportunity to the standard record. None if it has no title or URL."""
    if not isinstance(item, dict):
        return None
    title = _clean(item.get("title"))
    url = _clean(item.get("seo_url"))
    if not url and _clean(item.get("public_url")):
        url = f"{BASE_URL}/{_clean(item['public_url']).lstrip('/')}"
    if not title or not url.startswith(BASE_URL):
        return None  # unusable record, or a URL that doesn't point to the original Unstop page

    reg = item.get("regnRequirements") if isinstance(item.get("regnRequirements"), dict) else {}
    org = item.get("organisation") if isinstance(item.get("organisation"), dict) else {}
    location, mode = _location_and_mode(item)
    return {
        "title": title,
        "organization": _clean(org.get("name")),
        "start_date": _iso(item.get("start_date")),
        "end_date": _iso(item.get("end_date")),
        "registration_deadline": _iso(reg.get("end_regn_dt")),
        "location": location,
        "mode": mode,
        "prize": format_prize(item.get("prizes")),
        "description": html_to_text(item.get("details")),
        "url": url,
        "source": SOURCE,
        "scraped_at": scraped_at,
    }


# --------------------------------------------------------------------------- public API
def scrape(limit: Optional[int] = DEFAULT_LIMIT) -> list[dict[str, Any]]:
    """Scrape open Unstop hackathons. Returns standardized records; never raises.

    limit: max number of records (None = every open hackathon, ~25 pages, still rate limited).
    On any failure the records collected so far are returned (possibly an empty list).
    """
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json", "Accept-Language": "en"})
    started = time.monotonic()
    skipped = 0
    try:
        if not check_robots(session):
            log.warning("SKIPPED: robots.txt does not allow scraping %s", API_URL)
            return records
        page, last_page = 1, 1
        while page <= last_page and (limit is None or len(records) < limit):
            if page > 1:
                time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            payload = _get_page(session, page)
            block = payload.get("data") if isinstance(payload, dict) else None
            items = block.get("data") if isinstance(block, dict) else None
            if not isinstance(items, list):
                log.error("unexpected response shape on page %d; stopping", page)
                break
            last_page = int(block.get("last_page") or page)
            scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            for item in items:
                record = normalise(item, scraped_at)
                if record is None:
                    skipped += 1
                    continue
                if record["url"] in seen:  # duplicate
                    continue
                seen.add(record["url"])
                records.append(record)
                if limit is not None and len(records) >= limit:
                    break
            log.info("page %d/%d done: %d records so far", page, last_page, len(records))
            page += 1
    except _Blocked as exc:
        log.error("BLOCKED by Unstop (%s). Stopping; not retrying or bypassing.", exc)
    except Exception as exc:  # never crash the caller
        log.error("scrape stopped early: %s: %s", exc.__class__.__name__, exc)
    finally:
        session.close()
        log.info("done: %d records, %d skipped as invalid, %.1fs", len(records), skipped, time.monotonic() - started)
    return records


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # prize text contains the rupee sign
    records = scrape()
    print(f"\nCollected {len(records)} Unstop hackathon records. First 5:\n")
    for record in records[:5]:
        print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0 if records else 1


if __name__ == "__main__":
    sys.exit(main())
