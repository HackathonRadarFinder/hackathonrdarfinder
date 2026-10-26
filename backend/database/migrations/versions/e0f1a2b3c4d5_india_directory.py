"""Institution directory, announcement review and event geography."""
from alembic import op
import sqlalchemy as sa

revision = 'e0f1a2b3c4d5'
down_revision = 'd9e0f1a2b3c4'
branch_labels = depends_on = None


def upgrade():
    op.create_table('institutions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('identifier', sa.String(120), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('state', sa.String(100), nullable=False),
        sa.Column('district', sa.String(150)), sa.Column('city', sa.String(150)),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('website', sa.String(500)), sa.Column('website_verified_at', sa.DateTime()),
        sa.Column('event_urls', sa.JSON(), nullable=False), sa.Column('provenance', sa.JSON(), nullable=False),
        sa.Column('last_verified_at', sa.DateTime(), nullable=False),
        sa.Column('permission_status', sa.String(30), nullable=False))
    op.create_index('ix_institutions_state', 'institutions', ['state'])
    op.create_table('discovery_announcements',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('source_id', sa.Uuid(), sa.ForeignKey('sources.id'), nullable=False),
        sa.Column('institution_id', sa.Integer(), sa.ForeignKey('institutions.id')),
        sa.Column('fingerprint', sa.String(64), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False), sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('observed_at', sa.DateTime(), nullable=False), sa.Column('last_seen_at', sa.DateTime(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime()), sa.Column('reviewer_id', sa.Uuid(), sa.ForeignKey('users.id')),
        sa.Column('review_note', sa.Text()), sa.Column('hackathon_id', sa.Integer(), sa.ForeignKey('hackathons.id')),
        sa.UniqueConstraint('source_id', 'fingerprint', name='uq_announcement_revision'))
    op.create_index('ix_discovery_announcements_status', 'discovery_announcements', ['status'])
    op.add_column('hackathons', sa.Column('state', sa.String(100)))
    op.add_column('hackathons', sa.Column('institution_id', sa.Integer()))
    # batch mode supports SQLite and PostgreSQL without rebuilding existing event data manually.
    with op.batch_alter_table('hackathons') as batch:
        batch.create_foreign_key('fk_hackathons_institution', 'institutions', ['institution_id'], ['id'])
        batch.create_index('ix_hackathons_state', ['state'])
        batch.create_index('ix_hackathons_institution_id', ['institution_id'])
    op.add_column('hackathons', sa.Column('registration_url', sa.String(500)))
    op.add_column('hackathons', sa.Column('eligibility', sa.Text()))


def downgrade():
    with op.batch_alter_table('hackathons') as batch:
        batch.drop_constraint('fk_hackathons_institution', type_='foreignkey')
        batch.drop_index('ix_hackathons_state')
        batch.drop_index('ix_hackathons_institution_id')
        for name in ('state', 'institution_id', 'registration_url', 'eligibility'):
            batch.drop_column(name)
    op.drop_table('discovery_announcements')
    op.drop_table('institutions')
