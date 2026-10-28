"""Emit a real FastAPI response from synthetic approved API records in temporary SQLite."""
import json
import os
import sys
from pathlib import Path

os.environ['DATABASE_URL'] = 'sqlite+pysqlite://'
os.environ['SECRET_KEY'] = 'disposable-brabble-ui-test-secret-key-123456'
os.environ['DEBUG'] = 'false'
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app.main import app
from app.schemas.event import EventCreate
from app.services.brabble_adapter import normalize
from workers.import_reviewed_public import ACCEPT, ReviewedRecord, stage


def main():
    engine = create_engine('sqlite://', poolclass=StaticPool, connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    records = []
    for platform, url in [('Unstop', 'https://unstop.com/hackathons/brabble-ui-test'),
                          ('Devfolio', 'https://brabble-ui-test.devfolio.co/')]:
        raw = {'id': f'{platform.lower()}-ui-test', 'title': f'{platform} API UI test',
               'organiser': 'Disposable Test Organizers', 'platform': platform,
               'url': url, 'shareUrl': f'https://brabble.ai/s/{platform.lower()}-ui-test',
               'kind': 'competition', 'type': 'HACKATHON', 'deadline': '2026-11-01T12:00:00Z',
               'city': 'Test Venue', 'mode': 'ONLINE', 'prize': {'label': '₹18K'}}
        row = normalize(raw, {'acquired_at': '2026-10-25T17:25:58Z',
                              'source_refreshed_at': '2026-10-25T17:00:00Z'})
        row['acquisition_evidence']['verified_fields'] = ['organization', 'url', 'dates']
        from test_support.brabble_review import attest_row
        attest_row(row)
        records.append(ReviewedRecord(EventCreate.model_validate({key: row.get(key) or None for key in ACCEPT}),
                                      '', row['date_precision'], 'brabble_api', 'synthetic test authorization',
                                      row['acquisition_evidence']))
    with Session(engine) as db:
        stage(db, records, 'synthetic-ui-reviewer')
        db.commit()

    def database():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = database
    try:
        with TestClient(app) as client:
            response = client.get('/events/', params={'page': 1, 'page_size': 12})
            response.raise_for_status()
            Path(sys.argv[1]).write_text(json.dumps(response.json(), ensure_ascii=False), encoding='utf-8')
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


if __name__ == '__main__':
    main()
