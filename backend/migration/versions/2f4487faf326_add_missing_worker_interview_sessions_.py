"""add missing worker_interview_sessions, worker_skills, booking_chats tables and sync workers columns

Revision ID: 2f4487faf326
Revises: 1261877c8e44
Create Date: 2026-08-07 12:40:36.454071

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
import pgvector.sqlalchemy
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2f4487faf326'
down_revision: Union[str, Sequence[str], None] = '1261877c8e44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns(table_name)}
    return column_name in cols


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    """Create the worker onboarding tables that never made it into the database
    and backfill the workers table with the columns the SQLAlchemy model expects.

    Root causes addressed:
      * Issue 2 — GET /jobs/for-worker and GET /dispatch/match/{id}/find-help
        select from JobWorkerMatch, Job, WorkerProfile and WorkerSkill.
        Without the matched_skill_id column, worker_skills table, and the
        new WorkerProfile columns these SELECTs crash with UndefinedColumn.
      * Issue 3 — WorkerProfile.sync_profile_extracted_fields writes
        'specialities' (and other fields) to the workers table via
        upsert_worker_profile.  Without those columns the write fails and
        specialities never appear in the profile.
    """

    # ── 1. Enum type for WorkerSkill.skill_type ──────────────────────────────
    # (No separate CREATE TYPE — let sa.Enum handle it during create_table.)

    # ── 2. booking_chats table (FK target for jobs.booking_chat_id) ───────────
    if not _table_exists("booking_chats"):
        op.create_geospatial_table(
            "booking_chats",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("history", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("is_complete", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
            sa.Column("is_job_request", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
            sa.Column("categories", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("problem_description", sa.Text(), nullable=True),
        )

    # ── 3. worker_interview_sessions table ───────────────────────────────────
    if not _table_exists("worker_interview_sessions"):
        op.create_table(
            "worker_interview_sessions",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("history", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("stage", sa.String(), server_default="interviewing", nullable=False),
            sa.Column("is_complete", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
            sa.Column("is_rejected", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("pending_sub_skill", sa.Text(), nullable=True),
            sa.Column("pending_scenario", sa.Text(), nullable=True),
            sa.Column("has_verified_specialty", sa.Boolean(), nullable=True),
            sa.Column("scenario_score", sa.Integer(), nullable=True),
            sa.Column("scenario_passed", sa.Boolean(), nullable=True),
            sa.Column("profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("add_skill_turns", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )

    # ── 4. worker_skills table (must exist before matched_skill_id FK) ──────
    if not _table_exists("worker_skills"):
        op.create_table(
            "worker_skills",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True, index=True),
            sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("skill_type", sa.Enum("baseline", "speciality", name="worker_skill_type_enum"), nullable=False, index=True),
            sa.Column("stage", sa.String(length=50), nullable=False),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("embedding", pgvector.sqlalchemy.vector.VECTOR(dim=4096), nullable=True),
            sa.Column("scenario_question", sa.Text(), nullable=True),
            sa.Column("scenario_answer", sa.Text(), nullable=True),
            sa.Column("scenario_score", sa.Integer(), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False, index=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("certificate", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("license", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("misc", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("is_license", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
            sa.Column("is_certificate", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
            sa.Column("is_training", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        )

    # ── 5. customer_chat_data table (used by job_manager.upsert_chat_data) ───
    if not _table_exists("customer_chat_data"):
        op.create_geospatial_table(
            "customer_chat_data",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("booking_chat_id", sa.Integer(), nullable=False, unique=True, index=True),
            sa.Column("is_complete", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
            sa.Column("is_job_request", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
            sa.Column("problem_description", sa.Text(), nullable=False),
            sa.Column("categories", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("description_vector", pgvector.sqlalchemy.vector.VECTOR(dim=4096), nullable=True),
            sa.Column("location", Geography(geometry_type="POINT", srid=4326, dimension=2, spatial_index=False, from_text="ST_GeogFromText", name="geography"), nullable=True),
        )
        op.create_geospatial_index("idx_customer_chat_data_location", "customer_chat_data", ["location"], unique=False, postgresql_using="gist", postgresql_ops={})

    # ── 6. Add missing columns to workers table (idempotent) ──────────────────
    if not _has_column("workers", "user_id"):
        op.add_column("workers", sa.Column("user_id", sa.Integer(), nullable=True))
    if not _has_column("workers", "worker_chat_id"):
        op.add_column("workers", sa.Column("worker_chat_id", sa.Integer(), nullable=True, unique=True))
    if not _has_column("workers", "stage"):
        op.add_column("workers", sa.Column("stage", sa.String(length=50), nullable=True))
    if not _has_column("workers", "is_complete"):
        op.add_column("workers", sa.Column("is_complete", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False))
    if not _has_column("workers", "is_rejected"):
        op.add_column("workers", sa.Column("is_rejected", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False))
    if not _has_column("workers", "rejection_reason"):
        op.add_column("workers", sa.Column("rejection_reason", sa.Text(), nullable=True))
    if not _has_column("workers", "job_category"):
        op.add_column("workers", sa.Column("job_category", sa.String(length=100), nullable=True, index=True))
    if not _has_column("workers", "category_tag"):
        op.add_column("workers", sa.Column("category_tag", sa.String(length=100), nullable=True))
    if not _has_column("workers", "is_custom_category"):
        op.add_column("workers", sa.Column("is_custom_category", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False))
    if not _has_column("workers", "specialities"):
        op.add_column("workers", sa.Column("specialities", postgresql.ARRAY(sa.String(length=100)), nullable=False, server_default=sa.text("'{}'::character varying[]")))
    if not _has_column("workers", "specialized_tools_or_equipment"):
        op.add_column("workers", sa.Column("specialized_tools_or_equipment", postgresql.ARRAY(sa.String(length=100)), nullable=False, server_default=sa.text("'{}'::character varying[]")))
    if not _has_column("workers", "years_experience"):
        op.add_column("workers", sa.Column("years_experience", sa.Integer(), nullable=True, server_default=sa.text("0")))
    if not _has_column("workers", "license_or_certification"):
        op.add_column("workers", sa.Column("license_or_certification", sa.String(length=255), nullable=True))
    if not _has_column("workers", "job_description"):
        op.add_column("workers", sa.Column("job_description", sa.Text(), nullable=True))
    if not _has_column("workers", "emergency_available"):
        op.add_column("workers", sa.Column("emergency_available", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False))
    if not _has_column("workers", "has_verified_specialty"):
        op.add_column("workers", sa.Column("has_verified_specialty", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False))
    if not _has_column("workers", "scenario_passed"):
        op.add_column("workers", sa.Column("scenario_passed", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False))
    if not _has_column("workers", "scenario_score"):
        op.add_column("workers", sa.Column("scenario_score", sa.Integer(), server_default=sa.text("0"), nullable=False))
    if not _has_column("workers", "description_vector"):
        op.add_column("workers", sa.Column("description_vector", pgvector.sqlalchemy.vector.VECTOR(dim=4096), nullable=True))
    if not _has_column("workers", "phone_number"):
        op.add_column("workers", sa.Column("phone_number", sa.String(length=50), nullable=True))
    if not _has_column("workers", "address_text"):
        op.add_column("workers", sa.Column("address_text", sa.Text(), nullable=True))
    if not _has_column("workers", "latitude"):
        op.add_column("workers", sa.Column("latitude", sa.Float(), nullable=True))
    if not _has_column("workers", "longitude"):
        op.add_column("workers", sa.Column("longitude", sa.Float(), nullable=True))

    # Make location nullable (was NOT NULL in old schema, model expects nullable)
    bind = op.get_bind()
    inspector = inspect(bind)
    loc_col = next((c for c in inspector.get_columns("workers") if c["name"] == "location"), None)
    if loc_col and not loc_col["nullable"]:
        op.alter_column("workers", "location", existing_type=Geography(geometry_type="POINT", srid=4326, dimension=2, from_text="ST_GeogFromText", name="geography", nullable=False, _spatial_index_reflected=True), nullable=True)

    # Replace old self-FK (workers.id → users.id) with new FK (workers.user_id → users.id)
    fks = inspector.get_foreign_keys("workers")
    old_fk_exists = any(fk["name"] == "workers_id_fkey" for fk in fks)
    if old_fk_exists:
        op.drop_constraint("workers_id_fkey", "workers", type_="foreignkey")
    user_id_fk_exists = any("user_id" in fk.get("constrained_columns", []) for fk in fks)
    if not user_id_fk_exists:
        op.create_foreign_key("workers_user_id_fkey", "workers", "users", ["user_id"], ["id"], ondelete="CASCADE")

    # Drop old indexes on removed columns, add new ones
    indexes = inspector.get_indexes("workers")
    index_names = {idx["name"] for idx in indexes}
    if "ix_workers_category" in index_names:
        op.drop_index("ix_workers_category", table_name="workers")
    if "ix_workers_tags" in index_names:
        op.drop_index("ix_workers_tags", table_name="workers")

    bind = op.get_bind()
    inspector2 = inspect(bind)
    indexes2 = inspector2.get_indexes("workers")
    index_names2 = {idx["name"] for idx in indexes2}
    if not any("ix_workers_job_category" == n for n in index_names2):
        op.create_index(op.f("ix_workers_job_category"), "workers", ["job_category"], unique=False)
    if not any("ix_workers_user_id" == n for n in index_names2):
        op.create_index(op.f("ix_workers_user_id"), "workers", ["user_id"], unique=False)
    if not any("ix_workers_worker_chat_id" == n for n in index_names2):
        op.create_index(op.f("ix_workers_worker_chat_id"), "workers", ["worker_chat_id"], unique=False)

    # ── 7. Add matched_skill_id to job_worker_matches ────────────────────────
    if not _has_column("job_worker_matches", "matched_skill_id"):
        op.add_column("job_worker_matches", sa.Column("matched_skill_id", sa.Integer(), nullable=True, index=True))
    jwm_fks = inspector2.get_foreign_keys("job_worker_matches")
    if not any(fk.get("constrained_columns") == ["matched_skill_id"] for fk in jwm_fks):
        op.create_foreign_key(None, "job_worker_matches", "worker_skills", ["matched_skill_id"], ["id"], ondelete="SET NULL")

    # ── 8. Add missing FKs on jobs table ─────────────────────────────────────
    jobs_fks = inspector2.get_foreign_keys("jobs")
    if not any(fk.get("constrained_columns") == ["worker_id"] for fk in jobs_fks):
        op.create_foreign_key("jobs_worker_id_fkey", "jobs", "users", ["worker_id"], ["id"], ondelete="SET NULL")
    if not any(fk.get("constrained_columns") == ["booking_chat_id"] for fk in jobs_fks):
        op.create_foreign_key("jobs_booking_chat_id_fkey", "jobs", "booking_chats", ["booking_chat_id"], ["id"], ondelete="SET NULL")

    # ── 9. Add missing indexes on jobs table ─────────────────────────────────
    jobs_indexes = inspector2.get_indexes("jobs")
    jobs_idx_names = {idx["name"] for idx in jobs_indexes}
    if not any("idx_jobs_location" == n for n in jobs_idx_names):
        op.create_geospatial_index("idx_jobs_location", "jobs", ["location"], unique=False, postgresql_using="gist", postgresql_ops={})
    if not any("ix_jobs_customer_id" == n for n in jobs_idx_names):
        op.create_index(op.f("ix_jobs_customer_id"), "jobs", ["customer_id"], unique=False)
    if not any("ix_jobs_worker_id" == n for n in jobs_idx_names):
        op.create_index(op.f("ix_jobs_worker_id"), "jobs", ["worker_id"], unique=False)
    if not any("ix_jobs_mode" == n for n in jobs_idx_names):
        op.create_index(op.f("ix_jobs_mode"), "jobs", ["mode"], unique=False)
    if not any("ix_jobs_status" == n for n in jobs_idx_names):
        op.create_index(op.f("ix_jobs_status"), "jobs", ["status"], unique=False)


def downgrade() -> None:
    """Reverse the migration."""
    raise NotImplementedError("Downgrade for this migration is not provided — the schema additions are destructive and cannot be safely reversed.")
