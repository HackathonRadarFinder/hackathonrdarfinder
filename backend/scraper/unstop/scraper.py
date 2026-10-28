"""Offline Unstop opportunity normalization for the ingestion adapter.

Collection belongs to the governed collector engine. The former standalone
requests-based scraper was unused and could follow redirects without policy
checks; its network entry point is retired.
"""
from datetime import datetime
from html.parser import HTMLParser
import re
from typing import Any, Optional

SOURCE = "Unstop"
BASE_URL = "https://unstop.com"


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


def scrape(*args, **kwargs):
    """Retired compatibility entry point; refuses before any network activity."""
    raise RuntimeError("Standalone Unstop scraping is retired; use the governed collector engine and normalize_unstop_collection")
