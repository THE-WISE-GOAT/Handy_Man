"""fix_types_and_missing_columns

Revision ID: 24cc00094b4b
Revises: 50fe09d03459
Create Date: 2026-07-12 14:50:06.817859

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import reflection

# revision identifiers, used by Alembic.
revision: str = '24cc00094b4b'
down_revision: Union[str, Sequence[str], None] = '50fe09d03459'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema safely using dynamic inspection instead of try/except SQL blocks."""
    conn = op.get_bind()
    inspect_obj = reflection.Inspector.from_engine(conn)
    existing_tables = inspect_obj.get_table_names()

    # ----------------------------------------------------------------------
    # 1. Table: worker_interview_sessions
    # ----------------------------------------------------------------------
    if 'worker_interview_sessions' not in existing_tables:
        op.create_table(
            'worker_interview_sessions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('history', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column('stage', sa.String(), server_default='interviewing', nullable=False),
            sa.Column('is_complete', sa.Boolean(), server_default='FALSE', nullable=False),
            sa.Column('is_rejected', sa.Boolean(), server_default='FALSE', nullable=False),
            sa.Column('rejection_reason', sa.Text(), nullable=True),
            sa.Column('pending_sub_skill', sa.Text(), nullable=True),
            sa.Column('pending_scenario', sa.Text(), nullable=True),
            sa.Column('has_verified_specialty', sa.Boolean(), nullable=True),
            sa.Column('scenario_score', sa.Integer(), nullable=True),
            sa.Column('scenario_passed', sa.Boolean(), nullable=True),
            sa.Column('profile', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_worker_interview_sessions_id'), 'worker_interview_sessions', ['id'], unique=False)

    # ----------------------------------------------------------------------
    # 2. Cleanup jobs Table & Foreign Keys
    # ----------------------------------------------------------------------
    op.execute("ALTER TABLE IF EXISTS job_worker_matches DROP CONSTRAINT IF EXISTS job_worker_matches_job_id_fkey CASCADE")
    op.execute("DROP TABLE IF EXISTS jobs CASCADE")

    # ----------------------------------------------------------------------
    # 3. Table: booking_chats
    # ----------------------------------------------------------------------
    if 'booking_chats' in existing_tables:
        booking_cols = [c['name'] for c in inspect_obj.get_columns('booking_chats')]

        if 'categories' not in booking_cols:
            op.add_column('booking_chats', sa.Column('categories', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True))

        if 'history' in booking_cols:
            op.alter_column(
                'booking_chats', 'history',
                existing_type=postgresql.JSONB(astext_type=sa.Text()),
                type_=sa.JSON(),
                existing_nullable=False
            )

        for col in ['service_tags', 'problem_category', 'is_custom_category']:
            if col in booking_cols:
                op.drop_column('booking_chats', col)

    # ----------------------------------------------------------------------
    # 4. Table: workers
    # ----------------------------------------------------------------------
    if 'workers' in existing_tables:
        worker_cols = [c['name'] for c in inspect_obj.get_columns('workers')]
        worker_indexes = [i['name'] for i in inspect_obj.get_indexes('workers')]

        # Add missing columns
        columns_to_add = [
            ('user_id', sa.Column('user_id', sa.Integer(), nullable=False)),
            ('worker_chat_id', sa.Column('worker_chat_id', sa.Integer(), nullable=False)),
            ('stage', sa.Column('stage', sa.String(length=50), nullable=False)),
            ('is_complete', sa.Column('is_complete', sa.Boolean(), nullable=False)),
            ('is_rejected', sa.Column('is_rejected', sa.Boolean(), nullable=False)),
            ('rejection_reason', sa.Column('rejection_reason', sa.Text(), nullable=True)),
            ('job_category', sa.Column('job_category', sa.String(length=100), nullable=False)),
            ('category_tag', sa.Column('category_tag', sa.String(length=100), nullable=False)),
            ('is_custom_category', sa.Column('is_custom_category', sa.Boolean(), nullable=False)),
            ('specialities', sa.Column('specialities', postgresql.ARRAY(sa.String(length=100)), nullable=False)),
            ('specialized_tools_or_equipment', sa.Column('specialized_tools_or_equipment', postgresql.ARRAY(sa.String(length=100)), nullable=False)),
            ('license_or_certification', sa.Column('license_or_certification', sa.String(length=255), nullable=True)),
            ('job_description', sa.Column('job_description', sa.Text(), nullable=False)),
            ('emergency_available', sa.Column('emergency_available', sa.Boolean(), nullable=False)),
            ('has_verified_specialty', sa.Column('has_verified_specialty', sa.Boolean(), nullable=False)),
            ('scenario_passed', sa.Column('scenario_passed', sa.Boolean(), nullable=False)),
            ('scenario_score', sa.Column('scenario_score', sa.Integer(), nullable=False)),
            ('description_vector', sa.Column('description_vector', pgvector.sqlalchemy.vector.VECTOR(dim=4096), nullable=True)),
        ]

        for col_name, col_obj in columns_to_add:
            if col_name not in worker_cols:
                op.add_column('workers', col_obj)

        # Drop old indexes safely
        for idx in ['idx_workers_location', 'ix_workers_category', 'ix_workers_tags']:
            if idx in worker_indexes:
                op.drop_index(op.f(idx), table_name='workers')

        # Create new indexes safely
        if 'ix_workers_id' not in worker_indexes:
            op.create_index(op.f('ix_workers_id'), 'workers', ['id'], unique=False)
        if 'ix_workers_job_category' not in worker_indexes:
            op.create_index(op.f('ix_workers_job_category'), 'workers', ['job_category'], unique=False)
        if 'ix_workers_worker_chat_id' not in worker_indexes:
            op.create_index(op.f('ix_workers_worker_chat_id'), 'workers', ['worker_chat_id'], unique=True)

        # Foreign Key handling
        op.execute("ALTER TABLE workers DROP CONSTRAINT IF EXISTS workers_id_fkey CASCADE")
        op.create_foreign_key(None, 'workers', 'users', ['user_id'], ['id'], ondelete='CASCADE')

        # Drop old columns safely
        for col in ['operating_radius', 'category', 'tags', 'additional_metadata']:
            if col in worker_cols:
                op.drop_column('workers', col)

        # Drop geospatial location column cleanly
        op.execute("ALTER TABLE workers DROP COLUMN IF EXISTS location CASCADE")


def downgrade() -> None:
    """Downgrade schema safely."""
    conn = op.get_bind()
    inspect_obj = reflection.Inspector.from_engine(conn)
    existing_tables = inspect_obj.get_table_names()

    if 'workers' in existing_tables:
        worker_cols = [c['name'] for c in inspect_obj.get_columns('workers')]
        worker_indexes = [i['name'] for i in inspect_obj.get_indexes('workers')]

        if 'location' not in worker_cols:
            op.add_geospatial_column(
                'workers',
                sa.Column('location', Geography(geometry_type='POINT', srid=4326, dimension=2, spatial_index=False, from_text='ST_GeogFromText', name='geography', nullable=False), autoincrement=False, nullable=False)
            )

        if 'additional_metadata' not in worker_cols:
            op.add_column('workers', sa.Column('additional_metadata', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True))
        if 'tags' not in worker_cols:
            op.add_column('workers', sa.Column('tags', postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=False))
        if 'category' not in worker_cols:
            op.add_column('workers', sa.Column('category', sa.VARCHAR(), autoincrement=False, nullable=False))
        if 'operating_radius' not in worker_cols:
            op.add_column('workers', sa.Column('operating_radius', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False))

        op.execute("ALTER TABLE workers DROP CONSTRAINT IF EXISTS workers_user_id_fkey CASCADE")
        op.create_foreign_key(op.f('workers_id_fkey'), 'workers', 'users', ['id'], ['id'], ondelete='CASCADE')

        for idx in ['ix_workers_worker_chat_id', 'ix_workers_job_category', 'ix_workers_id']:
            if idx in worker_indexes:
                op.drop_index(op.f(idx), table_name='workers')

        if 'ix_workers_tags' not in worker_indexes:
            op.create_index(op.f('ix_workers_tags'), 'workers', ['tags'], unique=False)
        if 'ix_workers_category' not in worker_indexes:
            op.create_index(op.f('ix_workers_category'), 'workers', ['category'], unique=False)
        if 'idx_workers_location' not in worker_indexes:
            op.create_geospatial_index(op.f('idx_workers_location'), 'workers', ['location'], unique=False, postgresql_using='gist', postgresql_ops={})

        cols_to_remove = [
            'description_vector', 'scenario_score', 'scenario_passed', 'has_verified_specialty',
            'emergency_available', 'job_description', 'license_or_certification',
            'specialized_tools_or_equipment', 'specialities', 'is_custom_category',
            'category_tag', 'job_category', 'rejection_reason', 'is_rejected',
            'is_complete', 'stage', 'worker_chat_id', 'user_id'
        ]
        for col in cols_to_remove:
            if col in worker_cols:
                op.drop_column('workers', col)

    if 'booking_chats' in existing_tables:
        booking_cols = [c['name'] for c in inspect_obj.get_columns('booking_chats')]
        if 'is_custom_category' not in booking_cols:
            op.add_column('booking_chats', sa.Column('is_custom_category', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False))
        if 'problem_category' not in booking_cols:
            op.add_column('booking_chats', sa.Column('problem_category', sa.VARCHAR(), autoincrement=False, nullable=True))
        if 'service_tags' not in booking_cols:
            op.add_column('booking_chats', sa.Column('service_tags', postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True))

        if 'history' in booking_cols:
            op.alter_column(
                'booking_chats', 'history',
                existing_type=sa.JSON(),
                type_=postgresql.JSONB(astext_type=sa.Text()),
                existing_nullable=False
            )

    if 'jobs' not in existing_tables:
        op.create_table(
            'jobs',
            sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
            sa.Column('cust_id', sa.VARCHAR(), autoincrement=False, nullable=False),
            sa.Column('job_title', sa.VARCHAR(), autoincrement=False, nullable=False),
            sa.Column('job_desc', sa.TEXT(), autoincrement=False, nullable=False),
            sa.Column('professional', sa.VARCHAR(), autoincrement=False, nullable=True),
            sa.PrimaryKeyConstraint('id', name=op.f('jobs_pkey'))
        )

    if 'worker_interview_sessions' in existing_tables:
        op.execute("DROP TABLE IF EXISTS worker_interview_sessions CASCADE")