import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.hackathon import Hackathon
from workers.ingest_curated import ingest, validate_records
from test_account_integration import journey


def record(**changes):
    return {"title": "Reviewed event", "organization": "Reviewed organizer",
            "source": "Official organizer (manual)", "url": "https://example.org/event",
            "description": "Date precision: unavailable; no times assumed.",
            "scraped_at": "2026-10-13T00:00:00Z", **changes}


def test_reviewed_ingestion_dedup_and_caller_rollback(journey):
    _, _, _, engine = journey
    rows = validate_records([record()])
    with Session(engine) as db:
        assert ingest(db, rows)['inserted'] == 1
        assert ingest(db, rows)['duplicates'] == 1
        db.rollback()
    with Session(engine) as db:
        assert db.scalar(select(Hackathon).where(Hackathon.url == str(rows[0].url))) is None


@pytest.mark.parametrize('changes', [dict(url='http://example.org'), dict(url='https://u:p@example.org'),
    dict(source='approved scrape'), dict(description='missing provenance'), dict(scraped_at=None)])
def test_incomplete_provenance_rejected(changes):
    with pytest.raises(ValueError):
        validate_records([record(**changes)])
