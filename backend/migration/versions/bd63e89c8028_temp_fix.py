"""temp_fix

Revision ID: bd63e89c8028
Revises: 
Create Date: 2026-07-25

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# Ensure these match the exact missing revision ID string layout
revision: str = 'bd63e89c8028'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Leave empty so it executes safely as a dummy migration pass
    pass

def downgrade() -> None:
    pass
