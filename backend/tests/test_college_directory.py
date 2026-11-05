"""Approved public catalog and isolated private-schema authorization contracts."""
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.core.database import Base, get_db
from app.main import app
from app.models.core import User, Role
from app.models.institution import Institution
from app.core.security import create_access_token


def test_public_and_private_directories_are_separate(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'directory.db'}", connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.execute(text("ATTACH DATABASE ':memory:' AS aishe_staging"))
        db.execute(text('CREATE TABLE aishe_staging.colleges (identifier TEXT UNIQUE, name TEXT, state TEXT, district TEXT, permission_status TEXT)'))
        db.execute(text("INSERT INTO aishe_staging.colleges VALUES ('AISHE:PRIVATE-TEST','Private unit-test college','Assam','Kamrup','awaiting_permission')"))
        for i, approved in enumerate((False, True)):
            db.add(Institution(identifier=f'OFFICIAL:PUBLIC-TEST-{i}', name=f'Public fixture {i}', state='Assam',
                district='Kamrup', category='Test', last_verified_at=datetime(2026,1,1),
                permission_status='approved' if approved else 'awaiting_permission',
                provenance={'reuse_permitted': True, 'directory_publication_approved': True}))
        headers = {}
        for name in ('administrator', 'user', 'source_manager'):
            user = User(name='Unit test', email=f'{name}@example.org', password_hash='unused', roles=[Role(name=name)])
            db.add(user); db.flush()
            headers[name] = {'Authorization':'Bearer '+create_access_token(str(user.id),'administrator')}
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                for path in ('/colleges', '/institutions'):
                    result = client.get(path, params={'state':'assam','district':'kamrup'}).json()
                    assert result['total'] == 1
                    assert result['data'][0]['identifier'] == 'OFFICIAL:PUBLIC-TEST-1'
                    assert result['data'][0]['source_url'] is None
                    assert client.get(path+'?district=Other').json()['total'] == 0
                private = '/admin/discovery/institutions'
                assert client.get(private).status_code == 401
                for role in ('user', 'source_manager'):
                    assert client.get(private,headers=headers[role]).status_code == 403
                response = client.get(private,params={'q':'Private','state':'assam','district':'kamrup'},headers=headers['administrator'])
                assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
                assert response.json()['total'] == 1
                assert response.json()['data'][0]['identifier'] == 'AISHE:PRIVATE-TEST'
                assert client.get(private+'?q=%25',headers=headers['administrator']).json()['total'] == 0
                assert client.get(private+'?page=2',headers=headers['administrator']).json()['data'] == []
                assert client.get(private+'?page_size=101',headers=headers['administrator']).status_code == 422
                # Public query flags cannot select the private schema or override publication.
                assert client.get('/colleges?include_pending=true&q=Private').json()['total'] == 0
                assert client.get('/institutions/coverage').json()['total_universities'] == 1
        finally:
            app.dependency_overrides.clear()
    engine.dispose()
