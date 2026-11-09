"""State/district facets only expose published college directory rows."""
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models
from app.core.database import Base, get_db
from app.main import app
from app.models.institution import Institution


def test_public_state_and_dependent_district_facets(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / 'facets.db').as_posix()}",
                           connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False)

    def row(identifier, name, state, district, authorized):
        return Institution(identifier=identifier, name=name, state=state, district=district,
            category='Affiliated College', event_urls=[], last_verified_at=datetime.utcnow(),
            permission_status='awaiting_permission', provenance={
                'owner_publication_authorized': authorized,
                'collection_method': 'data_mined',
                'publication_scope': 'factual_fields_only'})
    with sessions() as db:
        db.add_all([
            row('AISHE:A1','First','Uttar Pradesh','Ghaziabad', True),
            row('AISHE:A2','Second','Uttar Pradesh','Meerut', True),
            row('AISHE:A3','Third','Delhi','Central', True),
            row('AISHE:A4','Unpublished','Kerala','Private District', False),
        ])
        db.commit()

    def override_db():
        with sessions() as db:
            yield db

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            empty = client.get('/institutions/facets')
            assert empty.status_code == 200, empty.text
            assert empty.json() == {'states': ['Delhi','Uttar Pradesh'], 'districts': []}
            up = client.get('/institutions/facets', params={'state':'uTTar pRadesh'})
            assert up.status_code == 200, up.text
            assert up.json()['districts'] == ['Ghaziabad','Meerut']
            assert client.get('/colleges/facets',params={'state':'Kerala'}).json()['districts'] == []
            assert client.get('/institutions',params={'state':'Uttar Pradesh','district':'Ghaziabad'}).json()['total'] == 1
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous
        engine.dispose()
