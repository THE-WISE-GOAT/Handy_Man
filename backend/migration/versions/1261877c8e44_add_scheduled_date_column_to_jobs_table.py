"""add scheduled_date column to jobs table

Revision ID: 1261877c8e44
Revises: 51d7d30a9ffb
Create Date: 2026-08-07 10:52:59.778476

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '1261877c8e44'
down_revision: Union[str, Sequence[str], None] = '51d7d30a9ffb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the missing scheduled_date column to the jobs table.

    This column was present in the SQLAlchemy model (model.py:358) but was
    never added to the database via an Alembic migration.  Any endpoint that
    references jobs.scheduled_date -- including GET /dispatch/match/{id}/find-help
    and POST /dispatch/{id}/complete -- raised a 500 ProgrammingError because the
    column did not exist in the PostgreSQL jobs table.

    Column is defined as nullable=True to match the model and preserve
    compatibility with existing rows.  The operation is idempotent: if the
    column already exists (e.g. added by Base.metadata.create_all at app
    startup), the migration is a no-op.
    """
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {col["name"] for col in inspector.get_columns("jobs")}
    if "scheduled_date" not in existing:
        op.add_column("jobs", sa.Column("scheduled_date", sa.Date(), nullable=True))


def downgrade() -> None:
    """Remove the scheduled_date column from the jobs table."""
    op.drop_column("jobs", "scheduled_date")
