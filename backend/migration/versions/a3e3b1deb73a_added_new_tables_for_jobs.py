"""Added new tables for jobs

Revision ID: a3e3b1deb73a
Revises: 1020062ac74a
Create Date: 2026-07-14 22:38:51.665878

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a3e3b1deb73a'
down_revision: Union[str, Sequence[str], None] = '1020062ac74a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema safely with IF EXISTS checks."""
    # 1. Drop chat_logs index and table safely
    op.execute("DROP INDEX IF EXISTS ix_chat_logs_id")
    op.execute("DROP TABLE IF EXISTS chat_logs CASCADE")

    # 2. Re-create geospatial index safely
    op.execute("DROP INDEX IF EXISTS idx_customer_chat_data_location")
    op.create_geospatial_index(
        'idx_customer_chat_data_location',
        'customer_chat_data',
        ['location'],
        unique=False,
        postgresql_using='gist',
        postgresql_ops={}
    )

    # 3. Drop column safely
    op.execute("ALTER TABLE customer_chat_data DROP COLUMN IF EXISTS job_title CASCADE")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('customer_chat_data', sa.Column('job_title', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    
    op.execute("DROP INDEX IF EXISTS idx_customer_chat_data_location")

    op.create_table('chat_logs',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('task_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('role_context', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('message_body', sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column('sender', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('timestamp', postgresql.TIMESTAMP(timezone=True), server_default=sa.text("'2026-07-05 05:39:04.337623+00'::timestamp with time zone"), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['service_tasks.id'], name=op.f('chat_logs_task_id_fkey'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('chat_logs_user_id_fkey'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('chat_logs_pkey'))
    )
    op.create_index(op.f('ix_chat_logs_id'), 'chat_logs', ['id'], unique=False)