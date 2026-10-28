"""Add discovery policy, run/evidence ledger and event snapshots."""
from alembic import op
import sqlalchemy as sa

revision = 'd9e0f1a2b3c4'
down_revision = 'c8d9e0f1a2b3'
branch_labels = depends_on = None


def upgrade():
    op.add_column('event_versions', sa.Column('snapshot', sa.JSON(), nullable=True))
    op.add_column('event_versions', sa.Column('changes', sa.JSON(), nullable=True))
    op.create_table('discovery_sources',
        sa.Column('source_id', sa.Uuid(), sa.ForeignKey('sources.id'), primary_key=True),
        sa.Column('key', sa.String(100), nullable=False, unique=True),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('interval_seconds', sa.Integer(), nullable=False),
        sa.Column('next_run_at', sa.DateTime(), nullable=False))
    op.create_table('discovery_runs',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('source_id', sa.Uuid(), sa.ForeignKey('sources.id'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime()),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('error_code', sa.String(64)),
        sa.Column('metrics', sa.JSON(), nullable=False))
    op.create_table('discovery_lock',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('run_id', sa.Uuid(), sa.ForeignKey('discovery_runs.id'), nullable=False))
    op.create_table('discovery_events',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('source_id', sa.Uuid(), sa.ForeignKey('sources.id'), nullable=False),
        sa.Column('canonical_url', sa.String(500), nullable=False),
        sa.Column('hackathon_id', sa.Integer(), sa.ForeignKey('hackathons.id'), nullable=False),
        sa.Column('last_observed_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('source_id', 'canonical_url', name='uq_discovery_identity'))
    op.create_table('discovery_evidence',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('hackathon_id', sa.Integer(), sa.ForeignKey('hackathons.id'), nullable=False),
        sa.Column('run_id', sa.Uuid(), sa.ForeignKey('discovery_runs.id'), nullable=False),
        sa.Column('source_id', sa.Uuid(), sa.ForeignKey('sources.id'), nullable=False),
        sa.Column('observed_at', sa.DateTime(), nullable=False),
        sa.Column('checksum', sa.String(64), nullable=False),
        sa.Column('document_url', sa.String(500), nullable=False),
        sa.Column('adapter_version', sa.String(64), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False))


def downgrade():
    for name in ('discovery_evidence', 'discovery_events', 'discovery_lock', 'discovery_runs', 'discovery_sources'):
        op.drop_table(name)
    op.drop_column('event_versions', 'changes')
    op.drop_column('event_versions', 'snapshot')
