"""stub

Revision ID: ba288dc72e9b
Revises: None
Create Date: 2026-08-07 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba288dc72e9b'
down_revision: Union[str, None] = '2f4487faf326'  # Link it to your other head
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Empty on purpose to bypass error
    pass


def downgrade() -> None:
    pass
