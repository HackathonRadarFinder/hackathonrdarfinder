"""merge investor and event migrations

Revision ID: 5dd552071c12
Revises: a16c6d0cc596, a2b3c4d5e6f7
Create Date: 2026-11-27 23:14:41.767105

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5dd552071c12'
down_revision: Union[str, Sequence[str], None] = ('a16c6d0cc596', 'a2b3c4d5e6f7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
