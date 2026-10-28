from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from radar_scraper import source_for, devfolio_links, parse_event, date_range, CollectionDenied, GovernedClient, collect


def test_source_allowlist():
    assert source_for("https://unstop.com/o/1754636") == "Unstop"
    assert source_for("https://hacknauts26.devfolio.co/") == "Devfolio"
    for url in ["http://unstop.com/o/2", "https://unstop.com.evil.tld/o/2", "https://127.0.0.1/x", "https://unstop.com/api/private"]:
        with pytest.raises(ValueError): source_for(url)


def test_date_range():
    assert date_range("Nov 14 - 15, 2026") == ("2026-11-14T00:00:00", "2026-11-15T00:00:00")
    assert date_range("31/10/26")[0] == "2026-10-31T00:00:00"


def test_discovery():
    listing = Path(__file__).resolve().parents[1] / "fixtures/devfolio_listing.html"
    links = devfolio_links(listing.read_text(encoding="utf-8"))
    assert links == ["https://hacknauts26.devfolio.co/", "https://devnexus2.devfolio.co/"]


def test_source_parser():
    fixtures = Path(__file__).resolve().parents[1] / "fixtures"
    from radar_scraper import read_urls
    import hashlib
    urls = read_urls(Path(__file__).resolve().parents[1] / "seed_urls.txt")
    parsed = []
    for url in urls:
        path = fixtures / (hashlib.sha256(url.encode()).hexdigest()[:16] + ".html")
        parsed.append(parse_event(url, path.read_text(encoding="utf-8")))
    assert len(parsed) == 4
    assert parsed[0]["start_date"] == "2026-11-14T00:00:00"
    assert parsed[0]["source"] == "Devfolio"
    assert parsed[2]["source"] == "Unstop"
    assert parsed[2]["prize"] == "₹ 90,000"
    assert all(item["review_status"] == "needs_review" for item in parsed)


def test_reject_cookie_wall():
    with pytest.raises(CollectionDenied):
        parse_event("https://unstop.com/o/123", "<html><body>Please Wait Error: Cookies Disabled</body></html>")


def test_permission_denied_without_network():
    client = GovernedClient({"Devfolio":{"approved": False,"basis":""}})
    with pytest.raises(CollectionDenied):
        client.fetch("https://hacknauts26.devfolio.co/")


def test_offline_collection(tmp_path):
    base = Path(__file__).resolve().parents[1]
    result = collect({}, base / "seed_urls.txt", tmp_path, discover=True, max_pages=20,
                     delay=1, offline=base / "fixtures")
    assert result["candidate_records"] == 4
    assert (tmp_path / "candidates.csv").exists()


def test_robots_disallow_fail_closed(monkeypatch):
    client = GovernedClient({"Devfolio": {"approved": True, "basis": "reviewed"}})
    monkeypatch.setattr(client, "get_raw", lambda url: (200, "User-agent: *\nDisallow: /", "text/plain"))
    with pytest.raises(CollectionDenied, match="robots.txt forbids"):
        client.verify_robots("https://hacknauts26.devfolio.co/")


def test_robots_bad_response_fail_closed(monkeypatch):
    client = GovernedClient({"Devfolio": {"approved": True, "basis": "reviewed"}})
    monkeypatch.setattr(client, "get_raw", lambda url: (500, "error", "text/plain"))
    with pytest.raises(CollectionDenied, match="Cannot verify robots"):
        client.verify_robots("https://hacknauts26.devfolio.co/")
