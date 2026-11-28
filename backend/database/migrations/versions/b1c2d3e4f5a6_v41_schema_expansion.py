"""v4.1 schema expansion (INT-01): hackathon fields, jobs, investors, platform tables and directory indexes.

One reversible migration for SRS Sec. 2, Sec. 8 and NFR-06. `alembic downgrade -1` removes everything added here.
Chained on develop's head a2b3c4d5e6f7 (INT-02 investor directory); the issue text names e0f1a2b3c4d5, which is no longer the head.
Investors, funds, startups and investments already exist (INT-02): this migration extends them and does not recreate them.
"""
from alembic import op
import sqlalchemy as sa

revision = 'b1c2d3e4f5a6'
down_revision = 'a2b3c4d5e6f7'
branch_labels = depends_on = None

# ======================================================================
# hackathon_fields
# ======================================================================
# New columns are nullable (or have a safe default) so existing rows keep working.
# A missing value means "unknown"; nothing is guessed or back-filled here.
COLUMNS = (
    ('category', sa.String(30)),            # college, corporate, community, government, startup, other
    ('tags', sa.JSON()),
    ('technologies', sa.JSON()),
    ('timezone', sa.String(64)),            # IANA name of the event's local timezone
    ('country', sa.String(100)),
    ('city', sa.String(150)),
    ('lifecycle_state', sa.String(20)),     # upcoming, active, completed, cancelled
    ('fee_details', sa.String(255)),
    ('first_seen_at', sa.DateTime()),
    ('last_seen_at', sa.DateTime()),
    ('last_checked_at', sa.DateTime()),
    ('evidence_url', sa.String(500)),
    ('verification_method', sa.String(100)),
    ('verified_at', sa.DateTime()),
    ('unpublished_reason', sa.String(100)),  # machine-readable reason code
)
INDEXES = (
    ('ix_hackathons_category', ['category']),
    ('ix_hackathons_country', ['country']),
    ('ix_hackathons_lifecycle_state', ['lifecycle_state']),
    ('ix_hackathons_category_start_date', ['category', 'start_date']),
    ('ix_hackathons_country_state', ['country', 'state']),
)


def _upgrade_hackathon_fields():
    for name, type_ in COLUMNS:
        op.add_column('hackathons', sa.Column(name, type_))
    # Existing events stay visible after the upgrade.
    op.add_column('hackathons', sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.true()))
    for name, cols in INDEXES:
        op.create_index(name, 'hackathons', cols)


def _downgrade_hackathon_fields():
    for name, _ in reversed(INDEXES):
        op.drop_index(name, table_name='hackathons')
    with op.batch_alter_table('hackathons') as batch:
        batch.drop_column('is_published')
        for name, _ in reversed(COLUMNS):
            batch.drop_column(name)

# ======================================================================
# jobs
# ======================================================================

def _upgrade_jobs():
    op.create_table('employers',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('normalized_name', sa.String(255), nullable=False),
        sa.Column('website', sa.String(500)),
        sa.Column('country', sa.String(100)),
        sa.Column('source_url', sa.String(500)),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('normalized_name', name='uq_employers_normalized_name'))
    op.create_table('jobs',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('employer_id', sa.Uuid(), sa.ForeignKey('employers.id'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('job_type', sa.String(30), nullable=False),          # job, internship, apprenticeship
        sa.Column('seniority', sa.String(30)),                         # entry, mid, senior (senior-only is excluded from fresher views)
        sa.Column('country', sa.String(100)),
        sa.Column('city', sa.String(150)),
        sa.Column('location_text', sa.String(255)),
        sa.Column('remote_mode', sa.String(20)),                       # remote, hybrid, onsite
        sa.Column('compensation_text', sa.String(255)),                # only when published by the source
        sa.Column('skills', sa.JSON()),
        sa.Column('eligibility', sa.Text()),
        sa.Column('experience_min_years', sa.Integer()),
        sa.Column('experience_max_years', sa.Integer()),
        sa.Column('apply_url', sa.String(500), nullable=False),
        sa.Column('canonical_url', sa.String(500)),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('source_url', sa.String(500)),
        sa.Column('external_id', sa.String(150)),                      # requisition / source job id
        sa.Column('posted_at', sa.DateTime()),
        sa.Column('first_published_at', sa.DateTime(), nullable=False),
        sa.Column('closes_at', sa.DateTime()),
        sa.Column('first_seen_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_seen_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_checked_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('archived_at', sa.DateTime()),
        sa.UniqueConstraint('source', 'external_id', name='uq_jobs_source_external_id'))
    op.create_index('ix_jobs_employer_id', 'jobs', ['employer_id'])
    op.create_index('ix_jobs_canonical_url', 'jobs', ['canonical_url'])
    op.create_index('ix_jobs_active_window', 'jobs', ['archived_at', 'first_published_at'])
    op.create_index('ix_jobs_type_country', 'jobs', ['job_type', 'country', 'first_published_at'])


def _downgrade_jobs():
    op.drop_index('ix_jobs_type_country', table_name='jobs')
    op.drop_index('ix_jobs_active_window', table_name='jobs')
    op.drop_index('ix_jobs_canonical_url', table_name='jobs')
    op.drop_index('ix_jobs_employer_id', table_name='jobs')
    op.drop_table('jobs')
    op.drop_table('employers')

# ======================================================================
# investors: provenance tables + extra columns on the INT-02 tables (SRS INV-01..INV-03)
# ======================================================================
_PROFILE_COLUMNS = (('country', sa.String(100)), ('region', sa.String(100)), ('city', sa.String(150)),
                    ('contact_channels', sa.JSON()), ('industries', sa.JSON()), ('stages', sa.JSON()))   # public channels only
_COMMON_COLUMNS = (('normalized_name', sa.String(255)), ('website', sa.String(500)), ('source_url', sa.String(500)),
                   ('created_at', sa.DateTime()), ('last_updated_at', sa.DateTime()))                     # NULL = unknown
_INVESTMENT_COLUMNS = (('announced_on', sa.Date()), ('co_investors', sa.JSON()), ('updated_at', sa.DateTime()))


def _upgrade_investors():
    op.create_table('source_evidence',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('source_url', sa.String(500), nullable=False),
        sa.Column('source_name', sa.String(150)),
        sa.Column('verification_method', sa.String(100)),
        sa.Column('verified_at', sa.DateTime()),
        sa.Column('observed_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_index('ix_source_evidence_source_url', 'source_evidence', ['source_url'])

    # Batch mode: SQLite cannot add a foreign-key column in place. On PostgreSQL these are plain ALTER TABLE statements.
    for table in ('investors', 'funds', 'startups'):
        with op.batch_alter_table(table) as batch:
            for name, type_ in _COMMON_COLUMNS:
                batch.add_column(sa.Column(name, type_))
            batch.add_column(sa.Column('merged_into_id', sa.Integer(), sa.ForeignKey(f'{table}.id', name=f'fk_{table}_merged_into_id')))  # set when a duplicate is merged
        op.create_index(f'ix_{table}_normalized_name', table, ['normalized_name'])
    for table in ('investors', 'funds'):
        with op.batch_alter_table(table) as batch:
            for name, type_ in _PROFILE_COLUMNS:
                batch.add_column(sa.Column(name, type_))
        op.create_index(f'ix_{table}_country', table, ['country'])
    op.add_column('funds', sa.Column('kind', sa.String(20)))          # firm or fund
    with op.batch_alter_table('investments') as batch:
        for name, type_ in _INVESTMENT_COLUMNS:
            batch.add_column(sa.Column(name, type_))
        batch.add_column(sa.Column('source_evidence_id', sa.Uuid(), sa.ForeignKey('source_evidence.id', name='fk_investments_source_evidence_id')))
    op.create_index('ix_investments_announced_on', 'investments', ['announced_on'])

    # entity_id points at investors, funds or startups (integer ids, chosen by entity_type), so it cannot be a database foreign key.
    op.create_table('entity_aliases',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('entity_type', sa.String(20), nullable=False),   # investor, fund or startup
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('alias', sa.String(255), nullable=False),
        sa.Column('alias_normalized', sa.String(255), nullable=False),
        sa.Column('verification_status', sa.String(20), nullable=False, server_default='unverified'),  # unverified, verified, disputed
        sa.Column('first_seen_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_seen_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('entity_type', 'entity_id', 'alias_normalized', name='uq_entity_alias'))
    op.create_index('ix_entity_aliases_alias_normalized', 'entity_aliases', ['alias_normalized'])

    # One alias can be backed by several sources, and one source can back several aliases.
    op.create_table('entity_alias_sources',
        sa.Column('alias_id', sa.Uuid(), sa.ForeignKey('entity_aliases.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('source_evidence_id', sa.Uuid(), sa.ForeignKey('source_evidence.id'), primary_key=True))
    op.create_index('ix_entity_alias_sources_source_evidence_id', 'entity_alias_sources', ['source_evidence_id'])

    op.create_table('entity_claims',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('entity_type', sa.String(20), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('value', sa.Text()),
        sa.Column('source_evidence_id', sa.Uuid(), sa.ForeignKey('source_evidence.id'), nullable=False),
        sa.Column('observed_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False))        # latest_confirmed, conflicting, superseded
    op.create_index('ix_entity_claims_entity', 'entity_claims', ['entity_type', 'entity_id', 'field_name'])


def _downgrade_investors():
    for table in ('entity_claims', 'entity_alias_sources', 'entity_aliases'):
        op.drop_table(table)
    op.drop_index('ix_investments_announced_on', table_name='investments')
    with op.batch_alter_table('investments') as batch:
        batch.drop_constraint('fk_investments_source_evidence_id', type_='foreignkey')
        batch.drop_column('source_evidence_id')
        for name, _ in reversed(_INVESTMENT_COLUMNS):
            batch.drop_column(name)
    with op.batch_alter_table('funds') as batch:
        batch.drop_column('kind')
    for table in ('investors', 'funds'):
        op.drop_index(f'ix_{table}_country', table_name=table)
        with op.batch_alter_table(table) as batch:
            for name, _ in reversed(_PROFILE_COLUMNS):
                batch.drop_column(name)
    for table in ('investors', 'funds', 'startups'):
        op.drop_index(f'ix_{table}_normalized_name', table_name=table)
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(f'fk_{table}_merged_into_id', type_='foreignkey')
            batch.drop_column('merged_into_id')
            for name, _ in reversed(_COMMON_COLUMNS):
                batch.drop_column(name)
    op.drop_table('source_evidence')


# ======================================================================
# platform
# ======================================================================

def _upgrade_platform():
    op.create_table('contacts',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('hackathon_id', sa.Integer(), sa.ForeignKey('hackathons.id')),
        sa.Column('employer_id', sa.Uuid(), sa.ForeignKey('employers.id')),
        sa.Column('investor_id', sa.Integer(), sa.ForeignKey('investors.id')),
        sa.Column('fund_id', sa.Integer(), sa.ForeignKey('funds.id')),
        sa.Column('name', sa.String(255)),
        sa.Column('designation', sa.String(255)),
        sa.Column('email', sa.String(320)),                    # public business email only
        sa.Column('phone', sa.String(50)),
        sa.Column('field_provenance', sa.JSON()),              # per-field source URL and verified time
        sa.Column('visibility', sa.String(20), nullable=False, server_default='public'),
        sa.Column('source_evidence_id', sa.Uuid(), sa.ForeignKey('source_evidence.id')),
        sa.Column('verified_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            '(CASE WHEN hackathon_id IS NULL THEN 0 ELSE 1 END + CASE WHEN employer_id IS NULL THEN 0 ELSE 1 END'
            ' + CASE WHEN investor_id IS NULL THEN 0 ELSE 1 END + CASE WHEN fund_id IS NULL THEN 0 ELSE 1 END) = 1',
            name='ck_contact_single_owner'))
    op.create_index('ix_contacts_hackathon_id', 'contacts', ['hackathon_id'])

    op.create_table('ingest_runs',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('area', sa.String(30), nullable=False),      # hackathons, jobs, investors, colleges
        sa.Column('source', sa.String(100)),
        sa.Column('status', sa.String(20), nullable=False),    # running, success, partial, failed
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime()),
        sa.Column('items_seen', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('items_new', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('items_updated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('items_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text()))
    op.create_index('ix_ingest_runs_area_status_finished', 'ingest_runs', ['area', 'status', 'finished_at'])

    op.create_table('alerts',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('kind', sa.String(30), nullable=False),      # saved_search, deadline, change
        sa.Column('query', sa.JSON()),
        sa.Column('channel', sa.String(20), nullable=False, server_default='in_app'),
        sa.Column('frequency', sa.String(20), nullable=False, server_default='daily'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('last_sent_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_index('ix_alerts_user_id', 'alerts', ['user_id'])


def _downgrade_platform():
    op.drop_index('ix_alerts_user_id', table_name='alerts')
    op.drop_table('alerts')
    op.drop_index('ix_ingest_runs_area_status_finished', table_name='ingest_runs')
    op.drop_table('ingest_runs')
    op.drop_index('ix_contacts_hackathon_id', table_name='contacts')
    op.drop_table('contacts')


# ======================================================================
# institutions: university + state/district indexes (AISHE import, NFR-06)
# ======================================================================
def _upgrade_directory():
    op.add_column('institutions', sa.Column('university', sa.String(255)))
    op.create_index('ix_institutions_district', 'institutions', ['district'])
    op.create_index('ix_institutions_state_district', 'institutions', ['state', 'district'])


def _downgrade_directory():
    op.drop_index('ix_institutions_state_district', table_name='institutions')
    op.drop_index('ix_institutions_district', table_name='institutions')
    with op.batch_alter_table('institutions') as batch:
        batch.drop_column('university')


def upgrade():
    _upgrade_hackathon_fields()
    _upgrade_jobs()
    _upgrade_investors()
    _upgrade_platform()
    _upgrade_directory()


def downgrade():
    _downgrade_directory()
    _downgrade_platform()
    _downgrade_investors()
    _downgrade_jobs()
    _downgrade_hackathon_fields()
