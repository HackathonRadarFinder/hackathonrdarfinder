"""Persistent email claims and outcomes, separate from in-app notifications.

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
"""
from alembic import op
import sqlalchemy as sa

revision = "c8d9e0f1a2b3"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "email_deliveries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("hackathon_id", sa.Integer(), sa.ForeignKey("hackathons.id"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("event_at", sa.DateTime(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("claimed_at", sa.DateTime()),
        sa.Column("accepted_at", sa.DateTime()),
        sa.Column("error_code", sa.String(40)),
        sa.UniqueConstraint("user_id", "hackathon_id", "kind", "event_at", name="uq_email_reminder"),
        sa.CheckConstraint("kind IN ('registration', 'upcoming')", name="ck_email_kind"),
        sa.CheckConstraint("status IN ('pending', 'sending', 'retry', 'accepted', 'failed', 'cancelled', 'unknown')", name="ck_email_status"),
        sa.CheckConstraint("attempts >= 0 AND attempts <= 3", name="ck_email_attempts"),
    )
    op.create_index("ix_email_delivery_due", "email_deliveries", ["status", "next_attempt_at"])


def downgrade():
    op.drop_index("ix_email_delivery_due", table_name="email_deliveries")
    op.drop_table("email_deliveries")
