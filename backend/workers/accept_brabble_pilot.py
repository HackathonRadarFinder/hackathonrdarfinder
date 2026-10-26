"""Accept reviewed real pilot data in disposable SQLite only; never use SessionLocal."""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db
from app.main import app
from app.models.hackathon import Hackathon
from workers.import_reviewed_public import load_approved, stage


def accept(csv_file, output):
    approved, skipped = load_approved(csv_file)
    if not approved:
        raise ValueError('Real-data acceptance requires at least one explicitly reviewed record')
    if any(row.acquisition_evidence['review']['reviewer_type'] == 'test_fixture' for row in approved):
        raise ValueError('Synthetic reviews cannot satisfy real-data acceptance')
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='radar-real-pilot-') as directory:
        engine = create_engine(f"sqlite:///{(Path(directory) / 'acceptance.db').as_posix()}",
                               connect_args={'check_same_thread': False})
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine)
        try:
            with factory() as db:
                dry_run = stage(db, approved, 'Codex disposable pilot acceptance')
                db.rollback()
                assert db.scalar(select(func.count()).select_from(Hackathon)) == 0
            with factory.begin() as db:
                imported = stage(db, approved, 'Codex disposable pilot acceptance')
            with factory.begin() as db:
                repeated = stage(db, approved, 'Codex disposable pilot acceptance')

            def database():
                with factory() as db:
                    yield db
            previous = dict(app.dependency_overrides)
            app.dependency_overrides[get_db] = database
            try:
                with TestClient(app) as client:
                    response = client.get('/events/', params={'page': 1, 'page_size': 1})
                    assert response.status_code == 200 and response.json()['total'] == len(approved)
                    pages = []
                    for page in range(1, len(approved) + 2):
                        result = client.get('/events/', params={'page': page, 'page_size': 1})
                        assert result.status_code == 200
                        pages.append(result.json())
                    items = [item for page in pages for item in page['data']]
                    assert len(items) == len(approved) and pages[-1]['data'] == []
                    details = []
                    for item in items:
                        result = client.get(f"/events/{item['id']}")
                        assert result.status_code == 200 and result.json()['data'] == item
                        assert item['acquisition']['provider'] == 'Brabble.ai'
                        assert item['acquisition']['method'] == 'brabble_api'
                        details.append(result.json())
                    full_response = client.get('/events/', params={'page': 1, 'page_size': 100}).json()
                    (output / 'events_response.json').write_text(json.dumps(full_response, ensure_ascii=False, indent=2), encoding='utf-8')
                    (output / 'detail_responses.json').write_text(json.dumps(details, ensure_ascii=False, indent=2), encoding='utf-8')
            finally:
                app.dependency_overrides.clear()
                app.dependency_overrides.update(previous)
        finally:
            engine.dispose()
    report = {'database': 'disposable temporary SQLite', 'configured_database_connected': False,
              'disposable_database_removed': True, 'reviewed_records': len(approved), 'not_approved': skipped,
              'dry_run': dry_run, 'dry_run_rollback_verified': True, 'imported': imported, 'repeat': repeated,
              'list_endpoint': 'passed', 'pagination': 'passed', 'detail_endpoints': 'passed',
              'brabble_attribution': 'passed', 'production_or_development_writes': False}
    (output / 'acceptance_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, default=Path('radar_collector/output/brabble-pilot/reviewed.csv'))
    parser.add_argument('--out', type=Path, default=Path('radar_collector/output/brabble-pilot/acceptance'))
    args = parser.parse_args()
    print(json.dumps(accept(args.csv, args.out), indent=2))


if __name__ == '__main__':
    main()
