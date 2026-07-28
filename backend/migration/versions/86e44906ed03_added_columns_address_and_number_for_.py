"""Added columns address and number for both worker and customer 

Revision ID: 86e44906ed03
Revises: ee0424fbcaff
Create Date: 2026-07-15 22:00:19.155251

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision: str = '86e44906ed03'
down_revision: Union[str, Sequence[str], None] = 'ee0424fbcaff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema safely using IF NOT EXISTS."""
    # Workers table additions
    op.execute("ALTER TABLE workers ADD COLUMN IF NOT EXISTS phone_number VARCHAR(50)")
    op.execute("ALTER TABLE workers ADD COLUMN IF NOT EXISTS address TEXT")

    # Customers / Customer chat data table additions (adjust table/column names if different in your file)
    op.execute("ALTER TABLE customer_chat_data ADD COLUMN IF NOT EXISTS phone_number VARCHAR(50)")
    op.execute("ALTER TABLE customer_chat_data ADD COLUMN IF NOT EXISTS address TEXT")


def downgrade() -> None:
    """Downgrade schema safely using IF EXISTS."""
    op.execute("ALTER TABLE workers DROP COLUMN IF EXISTS phone_number")
    op.execute("ALTER TABLE workers DROP COLUMN IF EXISTS address")
    op.execute("ALTER TABLE customer_chat_data DROP COLUMN IF EXISTS phone_number")
    op.execute("ALTER TABLE customer_chat_data DROP COLUMN IF EXISTS address")