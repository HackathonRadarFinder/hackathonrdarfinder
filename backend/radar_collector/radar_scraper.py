"""Public page discovery + review-only exports for Hackathon Radar Finder.

Never fetches without explicit site approval. Honors robots.txt and access errors,
never uses credentials, hidden endpoints, browser stealth, or CAPTCHA workarounds.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

USER_AGENT = "HackathonRadarFinderResearch/0.1"
MAX_BYTES = 2_000_000
FIELDS = ["title", "organization", "start_date", "end_date", "registration_deadline", "location", "mode",
          "prize", "description", "url", "source", "scraped_at", "team_size", "themes", "city", "state",
          "date_precision", "review_status", "issues", "source_hash", "collection_mode", "permission_reference", "acquisition_evidence"]


class CollectionDenied(Exception):
    """Permission, robots, HTTP challenge or source access check failed."""


def source_for(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port:
        raise ValueError(f"Only HTTPS public event URLs with no credentials/port: {url}")
    host = parsed.hostname.lower()
    if host in {"unstop.com", "www.unstop.com"}:
        if not re.match(r"^/(o/|hackathons/|competitions/)", parsed.path):
            raise ValueError(f"Unsupported Unstop URL path: {parsed.path}")
        return "Unstop"
    if host.endswith(".devfolio.co") and host not in {
        "assets.devfolio.co", "guide.devfolio.co", "blog.devfolio.co", "api.devfolio.co",
        "www.devfolio.co", "cdn.devfolio.co", "status.devfolio.co",
    }:
        return "Devfolio"
    if host == "devfolio.co" and parsed.path.rstrip("/") in {"/explore", "/hackathons"}:
        return "Devfolio listing"
    raise ValueError(f"Not a supported hackathon source: {url}")


def clean_url(url: str) -> str:
    p = urlsplit(url.strip())
    host = (p.hostname or "").lower()
    query = urlencode([(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
                       if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}])
    path = (p.path.rstrip("/") or "/")
    return urlunsplit((p.scheme.lower(), host, path, query, ""))


def compact(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def iso_day(value: str | None) -> str | None:
    """Calendar-day precision only. Naive midnight is a DB convention, NOT a known time."""
    if not value:
        return None
    try:
        return date_parser.parse(value, fuzzy=False, dayfirst=False).date().isoformat() + "T00:00:00"
    except (ValueError, TypeError, OverflowError):
        return None


def date_range(raw: str) -> tuple[str | None, str | None]:
    # Examples: 'Nov 14 - 15, 2026', 'November 14–15, 2026', '28/11/26'
    raw = compact(raw).replace("–", "-").replace("—", "-")
    m = re.search(r"\b([A-Za-z]{3,9})\s+(\d{1,2})\s*-\s*(\d{1,2}),?\s*(20\d{2})\b", raw)
    if m:
        month, d1, d2, year = m.groups()
        return iso_day(f"{month} {d1}, {year}"), iso_day(f"{month} {d2}, {year}")
    m = re.search(r"\b(\d{1,2})\s*-\s*(\d{1,2})\s+([A-Za-z]{3,9})\s+(20\d{2})\b", raw)
    if m:
        d1, d2, month, year = m.groups()
        return iso_day(f"{month} {d1}, {year}"), iso_day(f"{month} {d2}, {year}")
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b", raw)
    if m:
        d, mo, year = m.groups()
        year = "20" + year if len(year) == 2 else year
        try:
            return datetime(int(year), int(mo), int(d)).date().isoformat() + "T00:00:00", None
        except ValueError:
            return None, None
    return None, None


def line_after(lines: list[str], name: str) -> str:
    pattern = re.compile(r"^" + re.escape(name) + r"\s*:?\s*(.*)$", re.I)
    for i, ln in enumerate(lines):
        m = pattern.match(ln)
        if m:
            val = compact(m.group(1))
            return val if val else (lines[i+1] if i+1 < len(lines) else "")
    return ""


def labelled(lines: list[str], label: str) -> str:
    # More permissive matching for label decorated with emoji.
    for i, ln in enumerate(lines):
        m = re.search(r"\b" + re.escape(label) + r"\s*:\s*(.+)", ln, re.I)
        if m:
            return compact(m.group(1))
    return line_after(lines, label)


def parse_event(url: str, html: str, *, observed_at: str | None = None) -> dict:
    source = source_for(url)
    if source not in {"Unstop", "Devfolio"}:
        raise ValueError("Expected a source event page, not the listing")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    lines = [compact(x) for x in soup.stripped_strings if compact(x)]
    raw_text = "\n".join(lines)
    if len(raw_text) < 60 or re.search(r"Please Wait\s*Error: Cookies Disabled|enable cookies and Refresh|verify you are human|captcha", raw_text, re.I):
        raise CollectionDenied("HTML appears empty, JavaScript-only or an access challenge; no bypass attempted")
    h1 = soup.find("h1")
    meta = soup.find("meta", attrs={"property": "og:title"})
    title = compact(h1.get_text(" ", strip=True) if h1 else (meta.get("content", "") if meta else ""))
    if not title:
        raise ValueError("No event title in public HTML")
    desc_meta = soup.find("meta", attrs={"name": "description"})
    description = compact(desc_meta.get("content", "") if desc_meta else "")
    # Limit the description to protect the database; no copying entire site pages.
    if not description:
        description = compact(raw_text[:1500])
    description = description[:1000]
    row = {key: "" for key in FIELDS}
    row.update(title=title[:255], url=clean_url(url), source=source,
               scraped_at=observed_at or datetime.now(timezone.utc).isoformat(),
               description=description, review_status="needs_review",
               source_hash=hashlib.sha256(html.encode("utf-8")).hexdigest(),
               date_precision="unknown")

    if source == "Devfolio":
        # Devfolio pages expose 'Runs from' and 'Happening' in text.
        run_label = line_after(lines, "Runs from")
        if not run_label:
            match = re.search(r"\bDate\s*:\s*([^\n]+)", raw_text, re.I)
            run_label = match.group(1) if match else ""
        start, end = date_range(run_label)
        row["start_date"], row["end_date"] = start or "", end or ""
        if start: row["date_precision"] = "day"
        row["location"] = compact(line_after(lines, "Happening") or labelled(lines, "Venue"))[:255]
        mode_raw = labelled(lines, "Mode")
        if re.search(r"\bonline\b|\bvirtual\b", mode_raw, re.I): row["mode"] = "Online"
        elif re.search(r"\bhybrid\b", mode_raw, re.I): row["mode"] = "Hybrid"
        elif re.search(r"\boffline\b|\bin-person\b", mode_raw, re.I): row["mode"] = "Offline"
        elif row["location"]: row["mode"] = ""  # Physical city alone is not proof of mode.
        row["team_size"] = compact(labelled(lines, "Team Size"))[:80]
        org = re.search(r"\b(?:organized|organised) by\s+([\w&., '\-]{3,85}?)(?:[.\n]|\s+at\s)", raw_text, re.I)
        if org: row["organization"] = compact(org.group(1))[:255]
        prize = re.search(r"(?:\$|₹|€|£)\s*[\d,]+(?:\.\d+)?\s+Available in Prizes", raw_text, re.I)
        if prize: row["prize"] = prize.group(0).replace(" Available in Prizes", "")[:255]
    else:
        # Unstop HTML can be JS/cookie gated. Only trust labels actually present.
        headings = soup.find_all(["h1", "h2"], limit=10)
        for heading in headings:
            if heading.name == "h2" and heading.get_text(" ", strip=True):
                possible = compact(heading.get_text(" ", strip=True))
                if possible.lower() not in {"stages and timelines", "eligibility", "overview"} and "know about" not in possible.lower():
                    row["organization"] = possible[:255]
                    break
        reg = re.search(r"Registration Deadline\s*([0-3]?\d\s+[A-Za-z]{3,9}[ '’\d,:]+(?:IST|CUT|UTC)?)", raw_text, re.I)
        if reg:
            raw = reg.group(1).split("\n")[0].strip()
            # Do not map ambiguous 'CUT' to UTC or invent precise deadlines.
            if "CUT" not in raw.upper():
                try:
                    sanitized = re.sub(r"(\d{1,2})\s+([A-Za-z]{3})[’'](\d{2})", r"\1 \2 20\3", raw)
                    tz = {"IST": 5.5 * 3600, "UTC": 0}
                    dt = date_parser.parse(sanitized, tzinfos=tz, fuzzy=False)
                    if dt.tzinfo: row["registration_deadline"] = dt.isoformat()
                except (ValueError, OverflowError):
                    pass
        row["team_size"] = compact(labelled(lines, "Team Size"))[:80]
        loc = labelled(lines, "Location")
        if loc and not loc.lower().startswith("team size"):
            row["location"] = loc[:255]
        mode = re.search(r"\b(Online|Offline|Hybrid)\b", raw_text[:500], re.I)
        if mode: row["mode"] = mode.group(1).title()
        prize = re.search(r"Prizes worth\s*([₹$€£]\s*[\d,.]+)", raw_text, re.I)
        if prize: row["prize"] = compact(prize.group(1))[:255]
        # Typical pages include a clearly labelled overview section.
        m = re.search(r"All that you need to know about[^\n]*\n(.{40,1500})", raw_text, re.I | re.S)
        if m: row["description"] = compact(m.group(1))[:1000]

    # The parser is intentionally conservative: absent fields remain unknown.
    issues = []
    if not row["organization"]: issues.append("organization_missing")
    if not row["start_date"]: issues.append("event_start_date_unverified")
    if not row["registration_deadline"]: issues.append("registration_deadline_unverified")
    if not row["mode"]: issues.append("mode_unverified")
    if row["date_precision"] == "day":
        row["description"] = ("Date precision: day; 00:00 is a storage convention, not the announced event time. " + row["description"])[:1000]
    row["issues"] = "; ".join(issues)
    return row


def devfolio_links(html: str, limit: int = 30) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for a in soup.find_all("a", href=True):
        candidate = urljoin("https://devfolio.co/explore", a["href"])
        try:
            if source_for(candidate) != "Devfolio": continue
        except ValueError:
            continue
        # Reject transparent image/icon links and prefer event-name text.
        if not compact(a.get_text(" ", strip=True)): continue
        normalized = clean_url(candidate)
        if normalized not in urls: urls.append(normalized)
        if len(urls) >= limit: break
    return urls


class GovernedClient:
    def __init__(self, allowed: dict, delay: float = 2.0):
        self.allowed = allowed
        self.delay = max(delay, 1.0)
        self.session = requests.Session()
        contact = os.getenv("RADAR_CONTACT_EMAIL", "").strip()
        self.session.headers.update({"User-Agent": f"{USER_AGENT} (+mailto:{contact})" if contact else USER_AGENT,
                                     "Accept": "text/html,application/xhtml+xml"})
        if contact: self.session.headers["From"] = contact
        self.robots: dict[str, RobotFileParser] = {}
        self.last_request: float = 0.0

    def throttle(self):
        delta = time.monotonic() - self.last_request
        if delta < self.delay: time.sleep(self.delay - delta)
        self.last_request = time.monotonic()

    def get_raw(self, url: str) -> tuple[int, str, str]:
        self.throttle()
        r = self.session.get(url, timeout=(5, 15), allow_redirects=False, stream=True)
        try:
            if r.status_code in {301, 302, 303, 307, 308}:
                return r.status_code, "", r.headers.get("Location", "")
            if r.status_code in {401, 403, 429}:
                raise CollectionDenied(f"Site refused HTTP {r.status_code}; stop, do not bypass")
            content = bytearray()
            for chunk in r.iter_content(chunk_size=16384):
                content.extend(chunk)
                if len(content) > MAX_BYTES:
                    raise CollectionDenied("Response exceeded 2 MB limit")
            raw = content.decode(r.encoding or "utf-8", errors="replace")
            return r.status_code, raw, r.headers.get("Content-Type", "")
        finally:
            r.close()

    def verify_robots(self, url: str):
        p = urlsplit(url)
        origin = p.scheme + "://" + p.netloc
        if origin not in self.robots:
            robots_url = origin + "/robots.txt"
            status, raw, typ = self.get_raw(robots_url)
            if status in {404, 410}:
                raw = ""  # no robots policy published
            elif status != 200:
                raise CollectionDenied(f"Cannot verify robots at {robots_url} (HTTP {status})")
            parser = RobotFileParser()
            parser.parse(raw.splitlines())
            self.robots[origin] = parser
        if not self.robots[origin].can_fetch(USER_AGENT, url):
            raise CollectionDenied(f"robots.txt forbids {url}")

    def fetch(self, url: str) -> str:
        site = source_for(url)
        source = "Devfolio" if site == "Devfolio listing" else site
        policy = self.allowed.get(source, {})
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", os.getenv("RADAR_CONTACT_EMAIL", "").strip()):
            raise CollectionDenied("Set RADAR_CONTACT_EMAIL to a valid team contact before live collection")
        if policy.get("approved") is not True or not compact(policy.get("basis")):
            raise CollectionDenied(f"No documented source approval for {source}. See approvals.json")
        original_host = urlsplit(url).hostname
        for _ in range(3):
            self.verify_robots(url)
            status, raw, extra = self.get_raw(url)
            if status in {301, 302, 303, 307, 308}:
                next_url = urljoin(url, extra)
                if urlsplit(next_url).hostname != original_host:
                    raise CollectionDenied("Cross-host redirect refused")
                source_for(next_url)
                url = next_url
                continue
            if status != 200:
                raise CollectionDenied(f"HTTP {status}; no event extracted")
            if "html" not in extra.lower():
                raise CollectionDenied(f"Unexpected content type: {extra}")
            return raw
        raise CollectionDenied("Too many redirects")


def csv_safe(value):
    """Prefix spreadsheet formula-like values; importer removes only this safety prefix."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def save(rows: list[dict], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with (out / "candidates.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows([{key: csv_safe(value) for key, value in row.items()} for row in rows])
    (out / "candidates.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def read_urls(path: Path) -> list[str]:
    if not path.exists(): return []
    seen, result = set(), []
    for item in path.read_text(encoding="utf-8").splitlines():
        item = item.strip()
        if not item or item.startswith("#"): continue
        try:
            source = source_for(item)
            if source not in {"Unstop", "Devfolio"}: raise ValueError("not event")
            item = clean_url(item)
        except ValueError as e:
            print(f"SKIP invalid input: {e}", file=sys.stderr)
            continue
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def collect(approval: dict, seeds: Path, out: Path, *, discover: bool, max_pages: int, delay: float, offline: Path | None) -> dict:
    client = GovernedClient(approval, delay=delay)
    links = read_urls(seeds)
    failures = []
    if discover:
        try:
            html = (offline / "devfolio_listing.html").read_text(encoding="utf-8") if offline else client.fetch("https://devfolio.co/explore")
            links.extend(devfolio_links(html, limit=max_pages))
        except (OSError, requests.RequestException, CollectionDenied) as e:
            failures.append({"url": "https://devfolio.co/explore", "error": str(e)[:250]})
    dedup = []
    for url in links:
        if url not in dedup: dedup.append(url)
    results = []
    for url in dedup[:max_pages]:
        try:
            source = source_for(url)
            if offline:
                # Local fixture test mode: filenames are based on exact URL hashes.
                fixture = offline / (hashlib.sha256(url.encode()).hexdigest()[:16] + ".html")
                # Preserve source line endings: read_text() normalizes CRLF and
                # would hash different bytes from the evidence file on Windows.
                html = fixture.read_bytes().decode("utf-8")
            else:
                html = client.fetch(url)
            row = parse_event(url, html)
            row["collection_mode"] = "offline_fixture" if offline else "live_public"
            if not offline:
                row["permission_reference"] = compact(approval.get(source, {}).get("basis"))
            results.append(row)
            print(f"OK   {source:<9} {url}")
        except (ValueError, OSError, requests.RequestException, CollectionDenied) as e:
            failures.append({"url": url, "error": str(e)[:250]})
            print(f"SKIP {url} : {e}", file=sys.stderr)
    save(results, out)
    (out / "failures.json").write_text(json.dumps(failures, indent=2), encoding="utf-8")
    return {"candidate_records": len(results), "errors_or_denials": len(failures),
            "output": str(out.resolve()), "automatic_database_writes": False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed-file", type=Path, default=Path(__file__).with_name("seed_urls.txt"))
    ap.add_argument("--approvals", type=Path, default=Path(__file__).with_name("approvals.json"))
    ap.add_argument("--out", type=Path, default=Path(__file__).with_name("output"))
    ap.add_argument("--no-discovery", action="store_true", help="Only the seed URLs, not Devfolio listing")
    ap.add_argument("--max-pages", type=int, default=20)
    ap.add_argument("--delay", type=float, default=2)
    ap.add_argument("--offline-dir", type=Path, help="Read saved HTML fixtures only; makes no network requests")
    args = ap.parse_args()
    if not 1 <= args.max_pages <= 100: ap.error("--max-pages must be 1 to 100")
    approval = {} if args.offline_dir else json.loads(args.approvals.read_text(encoding="utf-8"))
    result = collect(approval, args.seed_file, args.out, discover=not args.no_discovery,
                     max_pages=args.max_pages, delay=args.delay, offline=args.offline_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
