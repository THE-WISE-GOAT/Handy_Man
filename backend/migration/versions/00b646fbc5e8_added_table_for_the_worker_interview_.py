"""Added table for the worker interview session

Revision ID: 00b646fbc5e8
Revises: 582dd0e56fac
Create Date: 2026-07-01 17:04:41.809803

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = '00b646fbc5e8'
down_revision: Union[str, Sequence[str], None] = '582dd0e56fac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "worker_interview_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("history", JSONB, nullable=False),
        sa.Column("stage", sa.String(), server_default="interviewing", nullable=False),
        sa.Column("is_complete", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_rejected", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("pending_sub_skill", sa.Text(), nullable=True),
        sa.Column("pending_scenario", sa.Text(), nullable=True),
        sa.Column("has_verified_specialty", sa.Boolean(), nullable=True),
        sa.Column("scenario_score", sa.Integer(), nullable=True),
        sa.Column("scenario_passed", sa.Boolean(), nullable=True),
        sa.Column("profile", JSONB, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False,
        ),
    )
    op.create_index(
        "ix_worker_interview_sessions_user_id",
        "worker_interview_sessions", ["user_id"],
    )
 
 
def downgrade() -> None:
    op.drop_index("ix_worker_interview_sessions_user_id", table_name="worker_interview_sessions")
    op.drop_table("worker_interview_sessions")
 