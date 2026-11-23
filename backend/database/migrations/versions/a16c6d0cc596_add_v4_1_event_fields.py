
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


def upgrade() -> None:
    op.add_column(
        "hackathons",
        sa.Column("category", sa.String(30), nullable=True)
    )
    op.add_column(
        "hackathons",
        sa.Column(
            "tags",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb")
        )
    )
    op.add_column(
        "hackathons",
        sa.Column("timezone", sa.String(64), nullable=True)
    )
    op.add_column(
        "hackathons",
        sa.Column("country", sa.String(100), nullable=True)
    )
    op.add_column(
        "hackathons",
        sa.Column("city", sa.String(100), nullable=True)
    )
    op.add_column(
        "hackathons",
        sa.Column("fees", sa.String(100), nullable=True)
    )
    op.add_column(
        "hackathons",
        sa.Column(
            "lifecycle_state",
            sa.String(20),
            nullable=False,
            server_default="upcoming"
        )
    )
    op.add_column(
        "hackathons",
        sa.Column("contacts", postgresql.JSONB(), nullable=True)
    )

    op.create_index(
        "ix_hackathons_category", "hackathons", ["category"]
    )
    op.create_index(
        "ix_hackathons_country", "hackathons", ["country"]
    )
    op.create_index(
        "ix_hackathons_city", "hackathons", ["city"]
    )
    op.create_index(
        "ix_hackathons_lifecycle_state",
        "hackathons",
        ["lifecycle_state"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_hackathons_lifecycle_state", table_name="hackathons"
    )
    op.drop_index("ix_hackathons_city", table_name="hackathons")
    op.drop_index("ix_hackathons_country", table_name="hackathons")
    op.drop_index("ix_hackathons_category", table_name="hackathons")

    op.drop_column("hackathons", "contacts")
    op.drop_column("hackathons", "lifecycle_state")
    op.drop_column("hackathons", "fees")
    op.drop_column("hackathons", "city")
    op.drop_column("hackathons", "country")
    op.drop_column("hackathons", "timezone")
    op.drop_column("hackathons", "tags")
    op.drop_column("hackathons", "category")
