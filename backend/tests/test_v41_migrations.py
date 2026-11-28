"""INT-01: the v4.1 migration is reversible, keeps existing rows, matches the ORM and enforces its constraints."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

BACKEND = Path(__file__).resolve().parents[1]
OLD_HEAD = 'a2b3c4d5e6f7'  # develop's head (INT-02 investor directory) before the v4.1 migration
FIRST_V41 = 'b1c2d3e4f5a6'
NEW_TABLES = {'employers', 'jobs', 'source_evidence', 'entity_aliases', 'entity_alias_sources', 'entity_claims',
              'contacts', 'ingest_runs', 'alerts'}  # investors, funds, startups and investments already exist (INT-02)
NEW_INVESTOR_COLUMNS = {'investors': {'normalized_name', 'website', 'source_url', 'created_at', 'last_updated_at', 'merged_into_id',
                                      'country', 'region', 'city', 'contact_channels', 'industries', 'stages'},
                        'funds': {'normalized_name', 'website', 'source_url', 'created_at', 'last_updated_at', 'merged_into_id',
                                  'country', 'region', 'city', 'contact_channels', 'industries', 'stages', 'kind'},
                        'startups': {'normalized_name', 'website', 'source_url', 'created_at', 'last_updated_at', 'merged_into_id'},
                        'investments': {'announced_on', 'co_investors', 'updated_at', 'source_evidence_id'}}
NEW_HACKATHON_COLUMNS = {'category', 'tags', 'technologies', 'timezone', 'country', 'city', 'lifecycle_state',
                         'fee_details', 'first_seen_at', 'last_seen_at', 'last_checked_at', 'evidence_url',
                         'verification_method', 'verified_at', 'unpublished_reason', 'is_published'}


@pytest.fixture
def url(tmp_path):
    return f"sqlite:///{(tmp_path / 'v41.db').as_posix()}"


def migrate(url, *args):
    env = {**os.environ, 'DATABASE_URL': url, 'SECRET_KEY': 'test-only-migration-secret-123456789', 'EMAIL_MODE': 'disabled'}
    result = subprocess.run([sys.executable, '-m', 'alembic', *args], cwd=BACKEND, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def engine_for(url):
    engine = create_engine(url)

    @event.listens_for(engine, 'connect')
    def _foreign_keys_on(dbapi_connection, _record):  # SQLite ignores foreign keys unless asked
        dbapi_connection.execute('PRAGMA foreign_keys=ON')
    return engine


@pytest.fixture
def engine(url):
    migrate(url, 'upgrade', 'head')
    engine = engine_for(url)
    yield engine
    engine.dispose()


def test_single_head_and_v41_migration_starts_at_previous_head():
    script = ScriptDirectory.from_config(Config(str(BACKEND / 'alembic.ini')))
    assert len(script.get_heads()) == 1
    assert script.get_revision(FIRST_V41).down_revision == OLD_HEAD


def test_upgrade_downgrade_upgrade_keeps_existing_rows(url):
    migrate(url, 'upgrade', OLD_HEAD)
    engine = engine_for(url)
    with engine.begin() as c:
        c.execute(text("INSERT INTO hackathons (title, state) VALUES ('Old Hack 1','Karnataka'),('Old Hack 2','Kerala')"))
        c.execute(text("INSERT INTO institutions (identifier, name, state, category, event_urls, provenance, last_verified_at, permission_status)"
                       " VALUES ('C-1','Test College','Karnataka','Engineering','[]','{}', CURRENT_TIMESTAMP, 'awaiting_permission')"))
        c.execute(text("INSERT INTO investors (id, name) VALUES (1, 'Existing Investor')"))
        c.execute(text("INSERT INTO startups (id, name, industry, country) VALUES (1, 'Existing Startup', 'Fintech', 'India')"))
        c.execute(text("INSERT INTO investments (investor_id, startup_id, stage) VALUES (1, 1, 'Seed')"))
    engine.dispose()

    migrate(url, 'upgrade', 'head')
    engine = engine_for(url)
    with engine.connect() as c:
        rows = c.execute(text('SELECT title, is_published, category, lifecycle_state FROM hackathons ORDER BY id')).all()
        assert [tuple(r) for r in rows] == [('Old Hack 1', 1, None, None), ('Old Hack 2', 1, None, None)]  # still published; new facts unknown
        assert NEW_TABLES <= set(inspect(c).get_table_names())
        for table, columns in NEW_INVESTOR_COLUMNS.items():
            assert columns <= {col['name'] for col in inspect(c).get_columns(table)}
        # INT-02 data is untouched and the new facts are unknown (NULL), not guessed
        assert tuple(c.execute(text('SELECT name, normalized_name, country FROM investors')).one()) == ('Existing Investor', None, None)
        assert tuple(c.execute(text('SELECT name, industry, country FROM startups')).one()) == ('Existing Startup', 'Fintech', 'India')
        assert tuple(c.execute(text('SELECT stage, announced_on FROM investments')).one()) == ('Seed', None)
        assert c.execute(text("SELECT university FROM institutions WHERE identifier='C-1'")).scalar() is None  # unknown, not guessed
        assert {'ix_institutions_state', 'ix_institutions_district', 'ix_institutions_state_district'} <= {i['name'] for i in inspect(c).get_indexes('institutions')}
        assert NEW_HACKATHON_COLUMNS <= {col['name'] for col in inspect(c).get_columns('hackathons')}
    engine.dispose()

    migrate(url, 'downgrade', OLD_HEAD)
    engine = engine_for(url)
    with engine.connect() as c:
        assert NEW_TABLES.isdisjoint(inspect(c).get_table_names())
        assert NEW_HACKATHON_COLUMNS.isdisjoint({col['name'] for col in inspect(c).get_columns('hackathons')})
        assert c.execute(text('SELECT count(*) FROM hackathons')).scalar() == 2
        assert c.execute(text('SELECT count(*) FROM institutions')).scalar() == 1
        for table, columns in NEW_INVESTOR_COLUMNS.items():
            assert columns.isdisjoint({col['name'] for col in inspect(c).get_columns(table)})
        assert [tuple(r) for r in c.execute(text('SELECT id, name FROM investors'))] == [(1, 'Existing Investor')]
        assert c.execute(text('SELECT stage FROM investments')).scalar() == 'Seed'
        assert 'university' not in {col['name'] for col in inspect(c).get_columns('institutions')}
    engine.dispose()
    migrate(url, 'upgrade', 'head')


def test_downgrade_minus_one_undoes_the_whole_v41_migration(url):
    migrate(url, 'upgrade', 'head')
    migrate(url, 'downgrade', '-1')
    engine = engine_for(url)
    with engine.connect() as c:
        assert NEW_TABLES.isdisjoint(inspect(c).get_table_names())
        assert 'university' not in {col['name'] for col in inspect(c).get_columns('institutions')}
    engine.dispose()
    migrate(url, 'upgrade', '+1')


def test_models_and_migrations_have_no_drift(engine):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from app import models  # noqa: F401  (registers every table on Base.metadata)
    from app.core.database import Base
    with engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []


def _fails(engine, *objects):
    with pytest.raises(IntegrityError):
        with Session(engine) as session:
            session.add_all(objects)
            session.commit()


def test_extended_investor_tables_keep_the_sourcing_rules(engine):
    from app.models import Fund, Investment, Investor, Startup
    with Session(engine) as session:
        investor, fund, startup = Investor(name='Jane Doe'), Fund(name='Blue Ridge', kind='fund'), Startup(name='Acme')
        session.add_all([investor, fund, startup])
        session.commit()
        investor_id, fund_id, startup_id = investor.id, fund.id, startup.id
        assert investor.created_at is not None and investor.merged_into_id is None  # timestamps are filled; merge target unknown
    _fails(engine, Investment(startup_id=startup_id))                                         # no investing party
    _fails(engine, Investment(startup_id=startup_id, investor_id=investor_id, fund_id=fund_id))  # two investing parties
    _fails(engine, Investment(startup_id=startup_id, fund_id=fund_id, check_size=1000))          # amount without currency and source
    _fails(engine, Investor(name='points at nobody', merged_into_id=999999))                      # merge target must exist
    with Session(engine) as session:
        session.add_all([Investment(startup_id=startup_id, fund_id=fund_id, stage='Seed'),
                         Investor(name='Jane D.', merged_into_id=investor_id)])
        session.commit()
        stored = session.query(Investment).one()
        assert stored.check_size is None and stored.updated_at is not None  # undisclosed stays NULL, never guessed


def test_contact_has_exactly_one_owner_and_foreign_keys_are_enforced(engine):
    from app.models import Contact, Employer, Hackathon
    with Session(engine) as session:
        hackathon, employer = Hackathon(title='T'), Employer(name='E', normalized_name='e')
        session.add_all([hackathon, employer])
        session.flush()
        hackathon_id, employer_id = hackathon.id, employer.id
        session.commit()
    _fails(engine, Contact(name='nobody owns me'))
    _fails(engine, Contact(hackathon_id=hackathon_id, employer_id=employer_id))
    _fails(engine, Contact(hackathon_id=999999))
    with Session(engine) as session:
        session.add(Contact(hackathon_id=hackathon_id, name='Organizer'))
        session.commit()
        assert session.query(Contact).one().visibility == 'public'


def test_job_defaults_and_source_identity_is_unique(engine):
    from datetime import datetime
    from app.models import Employer, Job
    with Session(engine) as session:
        employer = Employer(name='Acme', normalized_name='acme')
        session.add(employer)
        session.flush()
        employer_id = employer.id
        session.commit()

    def job(external_id):
        return Job(employer_id=employer_id, title='Graduate Engineer', job_type='job', apply_url='https://example.test/apply',
                   source='example', external_id=external_id, first_published_at=datetime(2026, 11, 20))
    with Session(engine) as session:
        session.add(job('R-1'))
        session.commit()
        stored = session.query(Job).one()
        assert stored.first_seen_at and stored.last_checked_at and stored.archived_at is None
    _fails(engine, job('R-1'))
    with Session(engine) as session:
        session.add(job('R-2'))
        session.commit()
    _fails(engine, Employer(name='ACME again', normalized_name='acme'))


def test_alias_is_unique_per_entity_but_may_be_ambiguous_across_entities(engine):
    from app.models import EntityAlias
    first, second = 11, 12
    with Session(engine) as session:
        session.add_all([EntityAlias(entity_type='fund', entity_id=first, alias='Sequoia', alias_normalized='sequoia'),
                         EntityAlias(entity_type='fund', entity_id=second, alias='Sequoia', alias_normalized='sequoia')])
        session.commit()
        assert {a.verification_status for a in session.query(EntityAlias)} == {'unverified'}
    _fails(engine, EntityAlias(entity_type='fund', entity_id=first, alias='SEQUOIA', alias_normalized='sequoia'))


def test_one_alias_can_have_several_sources_and_each_pair_is_stored_once(engine):
    import uuid
    from app.models import EntityAlias, EntityAliasSource, SourceEvidence
    with Session(engine) as session:
        alias = EntityAlias(entity_type='fund', entity_id=7, alias='Blue Ridge', alias_normalized='blue ridge')
        first = SourceEvidence(source_url='https://example.test/a')
        second = SourceEvidence(source_url='https://example.test/b')
        session.add_all([alias, first, second])
        session.flush()
        alias_id, first_id, second_id = alias.id, first.id, second.id
        session.add_all([EntityAliasSource(alias_id=alias_id, source_evidence_id=first_id),
                         EntityAliasSource(alias_id=alias_id, source_evidence_id=second_id)])
        session.commit()
        assert session.query(EntityAliasSource).filter_by(alias_id=alias_id).count() == 2
    _fails(engine, EntityAliasSource(alias_id=alias_id, source_evidence_id=first_id))  # same pair twice
    _fails(engine, EntityAliasSource(alias_id=uuid.uuid4(), source_evidence_id=first_id))  # unknown alias
