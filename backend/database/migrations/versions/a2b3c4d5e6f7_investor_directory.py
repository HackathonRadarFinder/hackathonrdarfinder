"""Add individuals, funds, startups, and sourced investments."""
from alembic import op
import sqlalchemy as sa

revision = "a2b3c4d5e6f7"
down_revision = "f1a2b3c4d5e6"
branch_labels = depends_on = None


def upgrade():
    for table in ("investors", "funds"):
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
        )
    op.create_table(
        "startups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("industry", sa.String(255)),
        sa.Column("country", sa.String(255)),
    )
    op.create_table(
        "investor_funds",
        sa.Column("investor_id", sa.Integer(), sa.ForeignKey("investors.id"), primary_key=True),
        sa.Column("fund_id", sa.Integer(), sa.ForeignKey("funds.id"), primary_key=True),
    )
    op.create_index("ix_investor_funds_fund_id", "investor_funds", ["fund_id"])
    op.create_table(
        "investments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("investor_id", sa.Integer(), sa.ForeignKey("investors.id")),
        sa.Column("fund_id", sa.Integer(), sa.ForeignKey("funds.id")),
        sa.Column("startup_id", sa.Integer(), sa.ForeignKey("startups.id"), nullable=False),
        sa.Column("stage", sa.String(100)),
        sa.Column("check_size", sa.Numeric(20, 4)),
        sa.Column("check_currency", sa.String(3)),
        sa.Column("check_source_url", sa.String(2048)),
        sa.Column("round_amount", sa.Numeric(20, 4)),
        sa.Column("round_currency", sa.String(3)),
        sa.Column("round_source_url", sa.String(2048)),
        sa.CheckConstraint(
            "(investor_id IS NULL) <> (fund_id IS NULL)",
            name="ck_investments_one_investing_party",
        ),
        sa.CheckConstraint(
            "check_size IS NULL OR (check_size >= 0 AND "
            "NULLIF(TRIM(check_currency), '') IS NOT NULL AND "
            "NULLIF(TRIM(check_source_url), '') IS NOT NULL)",
            name="ck_investments_sourced_check",
        ),
        sa.CheckConstraint(
            "round_amount IS NULL OR (round_amount >= 0 AND "
            "NULLIF(TRIM(round_currency), '') IS NOT NULL AND "
            "NULLIF(TRIM(round_source_url), '') IS NOT NULL)",
            name="ck_investments_sourced_round",
        ),
    )
    for column in ("investor_id", "fund_id", "startup_id"):
        op.create_index(f"ix_investments_{column}", "investments", [column])


def downgrade():
    for table in ("investments", "investor_funds", "startups", "funds", "investors"):
        op.drop_table(table)
