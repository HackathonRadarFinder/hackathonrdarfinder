
"""Add organizer contact details and field-level provenance."""
from alembic import op
import sqlalchemy as sa

revision = "f1a2b3c4d5e6"
down_revision = "e0f1a2b3c4d5"
branch_labels = depends_on = None


def upgrade():
    op.add_column(
        "hackathons",
        sa.Column("contacts", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_column("hackathons", "contacts")
