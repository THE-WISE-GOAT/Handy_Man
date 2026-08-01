"""add worker_skills table for per-skill embeddings, backfilling baseline rows

Replaces the single blended workers.description_vector with one independently
embedded row per capability, so a worker is matched on their BEST-fitting skill
instead of on an average of all of them.

Existing workers are backfilled: each gets one 'baseline' skill row carrying
their current job_description and description_vector, so seeded workers keep
matching immediately with no re-interview and no re-embedding cost.

workers.description_vector is intentionally LEFT IN PLACE. Dropping it would
make this migration irreversible without re-embedding every worker, and it is
still the source the backfill reads from. It is simply no longer read by the
matching engine.

Revision ID: f1a7c3d92b40
Revises: e37a941881b9
Create Date: 2026-07-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f1a7c3d92b40'
down_revision: Union[str, Sequence[str], None] = 'e37a941881b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. Safely create ENUM type
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'worker_skill_type_enum') THEN
                CREATE TYPE worker_skill_type_enum AS ENUM ('baseline', 'speciality');
            END IF;
        END
        $$;
    """)

    worker_skill_type_enum = postgresql.ENUM(
        'baseline', 'speciality', name='worker_skill_type_enum', create_type=False
    )

    # 2. Create worker_skills table
    if not inspector.has_table('worker_skills'):
        op.create_table(
            'worker_skills',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('worker_id', sa.Integer(), nullable=False),
            sa.Column('skill_type', worker_skill_type_enum, nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('embedding', pgvector.sqlalchemy.Vector(dim=4096), nullable=True),
            sa.Column('scenario_question', sa.Text(), nullable=True),
            sa.Column('scenario_answer', sa.Text(), nullable=True),
            sa.Column('scenario_score', sa.Integer(), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['worker_id'], ['workers.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_worker_skills_id'), 'worker_skills', ['id'])
        op.create_index(op.f('ix_worker_skills_worker_id'), 'worker_skills', ['worker_id'])
        op.create_index(op.f('ix_worker_skills_skill_type'), 'worker_skills', ['skill_type'])
        op.create_index(op.f('ix_worker_skills_is_active'), 'worker_skills', ['is_active'])

        op.create_index(
            'uq_worker_skills_one_baseline_per_worker',
            'worker_skills',
            ['worker_id'],
            unique=True,
            postgresql_where=sa.text("skill_type = 'baseline'"),
        )

    # 3. Backfill baseline rows using NOT EXISTS (avoids Postgres ON CONFLICT strictness)
    op.execute(
        """
        INSERT INTO worker_skills (
            worker_id, skill_type, title, description, embedding, is_active
        )
        SELECT
            w.id,
            'baseline'::worker_skill_type_enum,
            COALESCE(NULLIF(TRIM(w.job_category), ''), 'general work'),
            w.job_description,
            w.description_vector,
            TRUE
        FROM workers w
        WHERE TRIM(COALESCE(w.job_description, '')) <> ''
          AND NOT EXISTS (
              SELECT 1 FROM worker_skills ws
              WHERE ws.worker_id = w.id AND ws.skill_type = 'baseline'
          );
        """
    )

    # 4. Add matched_skill_id column to job_worker_matches
    matches_cols = [c['name'] for c in inspector.get_columns('job_worker_matches')]
    if 'matched_skill_id' not in matches_cols:
        op.add_column(
            'job_worker_matches',
            sa.Column('matched_skill_id', sa.Integer(), nullable=True),
        )
        op.create_index(
            op.f('ix_job_worker_matches_matched_skill_id'),
            'job_worker_matches',
            ['matched_skill_id'],
        )
        op.create_foreign_key(
            'fk_job_worker_matches_matched_skill_id',
            'job_worker_matches', 'worker_skills',
            ['matched_skill_id'], ['id'],
            ondelete='SET NULL',
        )

    # 5. Add add_skill_turns column to worker_interview_sessions
    session_cols = [c['name'] for c in inspector.get_columns('worker_interview_sessions')]
    if 'add_skill_turns' not in session_cols:
        op.add_column(
            'worker_interview_sessions',
            sa.Column('add_skill_turns', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    session_cols = [c['name'] for c in inspector.get_columns('worker_interview_sessions')]
    if 'add_skill_turns' in session_cols:
        op.drop_column('worker_interview_sessions', 'add_skill_turns')

    matches_cols = [c['name'] for c in inspector.get_columns('job_worker_matches')]
    if 'matched_skill_id' in matches_cols:
        op.drop_constraint(
            'fk_job_worker_matches_matched_skill_id', 'job_worker_matches', type_='foreignkey',
        )
        op.drop_index(op.f('ix_job_worker_matches_matched_skill_id'), table_name='job_worker_matches')
        op.drop_column('job_worker_matches', 'matched_skill_id')

    if inspector.has_table('worker_skills'):
        op.drop_index('uq_worker_skills_one_baseline_per_worker', table_name='worker_skills')
        op.drop_index(op.f('ix_worker_skills_is_active'), table_name='worker_skills')
        op.drop_index(op.f('ix_worker_skills_skill_type'), table_name='worker_skills')
        op.drop_index(op.f('ix_worker_skills_worker_id'), table_name='worker_skills')
        op.drop_index(op.f('ix_worker_skills_id'), table_name='worker_skills')
        op.drop_table('worker_skills')

    op.execute('DROP TYPE IF EXISTS worker_skill_type_enum CASCADE;')