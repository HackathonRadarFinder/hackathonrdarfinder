"""v4.1 acceptance tests for investor/portfolio deduplication, 'unknown' fields, and safe retries."""
from __future__ import annotations

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base


@pytest.fixture(params=["sqlite", "postgres"])
def db_engine(request, tmp_path):
    if request.param == "sqlite":
        url = f"sqlite+pysqlite:///{(tmp_path / 'investors_v41.db').as_posix()}"
        engine = create_engine(url)
    else:
        pg_url = os.getenv("RADAR_POSTGRES_ACCEPTANCE_URL")
        if not pg_url:
            pytest.skip("Set RADAR_POSTGRES_ACCEPTANCE_URL (via scripts/postgres_acceptance.py) for PostgreSQL 16 runs")
        engine = create_engine(pg_url, pool_pre_ping=True)

    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        if request.param == "sqlite":
            Base.metadata.drop_all(engine)
        engine.dispose()


def _normalize_name(name: str) -> str:
    return " ".join((name or "").strip().lower().split())


def _link_portfolio_without_duplicates(edges: list[dict]) -> list[dict]:
    deduped: dict[tuple[str, str], dict] = {}
    for edge in edges:
        inv_key = _normalize_name(edge["investor"])
        startup_key = _normalize_name(edge["startup"])
        pair = (inv_key, startup_key)
        check_size = edge.get("check_size_usd")
        normalized_check = "unknown" if check_size in (None, "", "unknown") else check_size
        source_url = edge.get("source_url") or "unknown"

        if pair not in deduped:
            deduped[pair] = {
                "investor": edge["investor"].strip(),
                "startup": edge["startup"].strip(),
                "check_size_usd": normalized_check,
                "sources": [source_url],
            }
        else:
            existing = deduped[pair]
            if existing["check_size_usd"] == "unknown" and normalized_check != "unknown":
                existing["check_size_usd"] = normalized_check
            if source_url not in existing["sources"]:
                existing["sources"].append(source_url)
    return list(deduped.values())


def test_investor_startup_linking_deduplicates_and_preserves_unknown(db_engine):
    raw_edges = [
        {"investor": "  Peak XV Partners ", "startup": "RadarAI", "check_size_usd": None, "source_url": "https://example.com/a"},
        {"investor": "peak xv partners", "startup": "radarai ", "check_size_usd": None, "source_url": "https://example.com/a"},
        {"investor": "Peak XV Partners", "startup": "RadarAI", "check_size_usd": 250000, "source_url": "https://example.com/b"},
        {"investor": "Undisclosed Angel", "startup": "CampusGrid", "check_size_usd": "", "source_url": None},
    ]

    with Session(db_engine) as session:
        assert session.is_active
        linked = _link_portfolio_without_duplicates(raw_edges)

    assert len(linked) == 2
    radar_link = next(item for item in linked if item["startup"] == "RadarAI")
    assert radar_link["check_size_usd"] == 250000
    assert radar_link["sources"] == ["https://example.com/a", "https://example.com/b"]

    campus_link = next(item for item in linked if item["startup"] == "CampusGrid")
    assert campus_link["check_size_usd"] == "unknown"
    assert campus_link["sources"] == ["unknown"]


def test_collector_retries_safely_on_transient_failure():
    attempts = {"count": 0}

    def flaky_collector():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise TimeoutError("temporary upstream timeout")
        return [{"investor": "100X.VC", "startup": "FinPulse", "check_size_usd": None}]

    result = None
    max_retries = 3
    for _ in range(max_retries):
        try:
            result = flaky_collector()
            break
        except TimeoutError:
            continue

    assert attempts["count"] == 3
    assert result is not None
    linked = _link_portfolio_without_duplicates(result)
    assert linked[0]["check_size_usd"] == "unknown"
