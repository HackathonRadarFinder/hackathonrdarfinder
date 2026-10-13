"""Loopback MVP with reviewed real events in a temporary SQLite database.

No live database, crawling, seeded credentials or email delivery. The database
lasts until this process stops; account data is deliberately disposable.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8021)
    parser.add_argument('--check', action='store_true', help='Check migrations, ingestion and API; then exit')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Use a port between 1024 and 65535')
    root = Path(__file__).resolve().parents[1]
    backend = root / 'backend'
    sys.path.insert(0, str(backend))
    with tempfile.TemporaryDirectory(prefix='radar-curated-demo-') as temporary:
        os.environ.update(
            DATABASE_URL=f"sqlite:///{Path(temporary).as_posix()}/demo.sqlite3",
            SECRET_KEY=secrets.token_urlsafe(48), ENVIRONMENT='development',
            DEBUG='false', EMAIL_MODE='disabled', SMTP_HOST='',
            SMTP_USERNAME='', SMTP_PASSWORD='', PYTHONDONTWRITEBYTECODE='1',
        )
        subprocess.run([sys.executable, '-B', '-m', 'alembic', 'upgrade', 'head'],
                       cwd=backend, env=os.environ, check=True)
        from app.core.database import engine, SessionLocal
        from workers.ingest_curated import ingest, validate_records
        from app.main import app
        records = validate_records(json.loads((backend / 'data' / 'curated-mvp-20261013.json').read_text(encoding='utf-8')))
        try:
            with SessionLocal() as db:
                initial = ingest(db, records)
                db.commit()
                repeated = ingest(db, records)
                db.commit()
            assert initial == {'inserted': len(records), 'duplicates': 0}
            assert repeated == {'inserted': 0, 'duplicates': len(records)}

            @app.get('/__local_demo', include_in_schema=False)
            def demo_marker():
                return {'database': 'temporary-curated-local-demo', 'email': 'disabled',
                        'records': len(records), 'source': 'reviewed-curated-snapshot'}

            if args.check:
                from fastapi.testclient import TestClient
                with TestClient(app) as client:
                    page = client.get('/events/', params={'page': 1, 'page_size': 100})
                    assert page.status_code == 200 and page.json()['total'] == len(records)
                    row = page.json()['data'][0]
                    assert client.get(f"/events/{row['id']}").json()['data']['url'] == row['url']
                    assert client.get('/predictions/catalog').json()['data'] == []
                    assert client.get('/admin/stats').status_code in (401, 403)
                print(json.dumps({'check': 'passed', 'events': len(records),
                                  'repeat_import_duplicates': repeated['duplicates'], 'email': 'disabled'}))
                return 0
            print(f'Curated local demo backend: http://127.0.0.1:{args.port}', flush=True)
            print('Reviewed snapshot imported; email disabled. Register your own disposable account.', flush=True)
            print('Account changes last until this server stops. Existing databases are untouched.', flush=True)
            import uvicorn
            uvicorn.run(app, host='127.0.0.1', port=args.port, log_level='warning')
        finally:
            engine.dispose()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
