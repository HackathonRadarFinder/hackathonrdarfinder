"""Loopback-only browser fixture serving genuinely reviewed records from temporary SQLite."""
import argparse
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.update(DATABASE_URL='sqlite+pysqlite://', DEBUG='false', ENVIRONMENT='development',
                  SECRET_KEY='temporary-real-pilot-browser-secret-123456', EMAIL_MODE='disabled',
                  DISCOVERY_ENABLED='false')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

import uvicorn
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.core.database import Base, get_db
from app.main import app
from workers.import_reviewed_public import load_approved, stage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, required=True)
    args = parser.parse_args()
    csv = Path(__file__).resolve().parents[1] / 'backend/radar_collector/output/brabble-pilot/reviewed.csv'
    records, skipped = load_approved(csv)
    if not records or skipped or any(r.acquisition_evidence['review']['reviewer_type'] == 'test_fixture' for r in records):
        raise ValueError('Browser acceptance requires genuine reviewed records only')
    with TemporaryDirectory(prefix='radar-pilot-browser-') as directory:
        engine = create_engine(f"sqlite:///{(Path(directory) / 'browser.db').as_posix()}",
                               connect_args={'check_same_thread': False})
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine)
        with factory.begin() as db:
            stage(db, records, 'Codex disposable browser acceptance')

        def database():
            with factory() as db:
                yield db
        app.dependency_overrides[get_db] = database
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=args.port, log_level='warning'))

        @app.get('/__pilot_acceptance', include_in_schema=False)
        def marker():
            return {'database': 'temporary-reviewed-brabble-pilot', 'records': len(records),
                    'configured_database_connected': False, 'email': 'disabled', 'discovery': 'disabled'}

        @app.post('/__pilot_shutdown', include_in_schema=False)
        def shutdown():
            server.should_exit = True
            return {'stopping': True}
        try:
            server.run()
        finally:
            app.dependency_overrides.clear()
            engine.dispose()


if __name__ == '__main__':
    main()
