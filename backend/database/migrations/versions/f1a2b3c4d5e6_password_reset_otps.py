"""Hashed email OTP password resets and revocable login token generation."""
from alembic import op
import sqlalchemy as sa

revision = 'f1a2b3c4d5e6'
down_revision = 'e0f1a2b3c4d5'
branch_labels = depends_on = None


def upgrade():
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'))
    op.create_table('password_reset_otps',
        sa.Column('email_key', sa.String(64), primary_key=True),
        sa.Column('code_digest', sa.String(64), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('window_started_at', sa.DateTime(), nullable=False),
        sa.Column('requests_in_window', sa.Integer(), nullable=False))
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('ALTER TABLE password_reset_otps ENABLE ROW LEVEL SECURITY')
        op.execute('REVOKE ALL ON TABLE password_reset_otps FROM PUBLIC, anon, authenticated')


def downgrade():
    op.drop_table('password_reset_otps')
    op.drop_column('users', 'token_version')
