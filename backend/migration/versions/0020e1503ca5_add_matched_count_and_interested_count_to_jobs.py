"""add_matched_count_and_interested_count_to_jobs

Revision ID: 0020e1503ca5
Revises: 86e44906ed03
Create Date: 2026-07-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0020e1503ca5'
down_revision: Union[str, Sequence[str], None] = '86e44906ed03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Safely add columns only if the jobs table exists."""
    op.execute("ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS matched_count INTEGER DEFAULT 0 NOT NULL")
    op.execute("ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS interested_count INTEGER DEFAULT 0 NOT NULL")


def downgrade() -> None:
    """Safely drop columns if the jobs table exists."""
    op.execute("ALTER TABLE IF EXISTS jobs DROP COLUMN IF EXISTS matched_count")
    op.execute("ALTER TABLE IF EXISTS jobs DROP COLUMN IF EXISTS interested_count")