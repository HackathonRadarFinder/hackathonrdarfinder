"""add v4.1 event fields

Revision ID: a16c6d0cc596
Revises: f1a2b3c4d5e6
Create Date: 2026-11-20 20:52:02.763335
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a16c6d0cc596'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# JSONB on PostgreSQL, plain JSON on other databases (tests run on SQLite).
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column("hackathons", sa.Column("category", sa.String(30), nullable=True))
    op.add_column(
        "hackathons",
        sa.Column("tags", JSON_TYPE, nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column("hackathons", sa.Column("timezone", sa.String(64), nullable=True))
    op.add_column("hackathons", sa.Column("country", sa.String(100), nullable=True))
    op.add_column("hackathons", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("hackathons", sa.Column("fees", sa.String(100), nullable=True))
    op.add_column(
        "hackathons",
        sa.Column("lifecycle_state", sa.String(20), nullable=False, server_default="upcoming"),
    )
    op.add_column("hackathons", sa.Column("contacts", JSON_TYPE, nullable=True))

    op.create_index("ix_hackathons_category", "hackathons", ["category"])
    op.create_index("ix_hackathons_country", "hackathons", ["country"])
    op.create_index("ix_hackathons_city", "hackathons", ["city"])
    op.create_index("ix_hackathons_lifecycle_state", "hackathons", ["lifecycle_state"])


def downgrade() -> None:
    op.drop_index("ix_hackathons_lifecycle_state", table_name="hackathons")
    op.drop_index("ix_hackathons_city", table_name="hackathons")
    op.drop_index("ix_hackathons_country", table_name="hackathons")
    op.drop_index("ix_hackathons_category", table_name="hackathons")

    with op.batch_alter_table("hackathons") as batch_op:
        batch_op.drop_column("contacts")
        batch_op.drop_column("lifecycle_state")
        batch_op.drop_column("fees")
        batch_op.drop_column("city")
        batch_op.drop_column("country")
        batch_op.drop_column("timezone")
        batch_op.drop_column("tags")
        batch_op.drop_column("category")