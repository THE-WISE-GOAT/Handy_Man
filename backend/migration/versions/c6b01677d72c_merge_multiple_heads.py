"""merge_multiple_heads

Revision ID: c6b01677d72c
Revises: a9fdad22593b, bd63e89c8028
Create Date: 2026-07-25 12:44:51.712347

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision: str = 'c6b01677d72c'
down_revision: Union[str, Sequence[str], None] = ('a9fdad22593b', 'bd63e89c8028')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
