"""
Worker profile write helpers — keeping WorkerProfile and its WorkerSkill rows
in sync.

WHY THIS MODULE LOOKS DIFFERENT THAN IT USED TO
-----------------------------------------------
The previous version had two functions:

  * sync_profile_extracted_fields — a hand-maintained field-by-field copy from
    the extracted profile dict onto the ORM row. It silently dropped any new
    field until someone remembered to add a line, and its import in
    chat_worker.py was commented out with the logic inlined instead.
  * upsert_worker_expertise — wrote to model.WorkerExpertise, a class that does
    not exist. The underlying `worker_expertises` table was dropped in migration
    e37a941881b9, so this was dead code referencing a deleted table.

Both are replaced here by helpers built around `worker_skills`, the table that
actually carries the per-skill vectors matching depends on.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core import model

logger = logging.getLogger(__name__)

# Fields on WorkerProfile that the extracted profile dict is allowed to set.
# An explicit allowlist, not hasattr(): the extracted dict now also carries
# baseline_description / speciality_* keys that belong on worker_skills rows,
# not on the parent, and a blind copy would either crash or write junk.
_EXTRACTED_PROFILE_FIELDS = frozenset({
    "job_category",
    "category_tag",
    "is_custom_category",
    "specialities",
    "specialized_tools_or_equipment",
    "years_experience",
    "license_or_certification",
    "job_description",
    "emergency_available",
    "has_verified_specialty",
    "scenario_passed",
    "scenario_score",
})


def sync_profile_extracted_fields(profile: model.WorkerProfile, extracted: dict) -> None:
    """
    Copy the AI-extracted fields onto a WorkerProfile row.

    Only keys in _EXTRACTED_PROFILE_FIELDS are copied, so layer-specific text
    (baseline_description, speciality_description) cannot leak onto the parent
    row where it has no column and no meaning.

    None is never written over an existing value for NOT NULL columns — a
    partially-failed extraction should degrade the profile, not break the row.
    """
    if not extracted:
        return

    for key, value in extracted.items():
        if key not in _EXTRACTED_PROFILE_FIELDS:
            continue
        if value is None:
            continue
        setattr(profile, key, value)

    # Normalise the list columns, which are NOT NULL with a list default.
    if profile.specialities is None:
        profile.specialities = []
    if profile.specialized_tools_or_equipment is None:
        profile.specialized_tools_or_equipment = []


def upsert_baseline_skill(
    db: Session,
    worker_id: int,
    title: str,
    description: str,
    embedding: list[float] | None,
) -> model.WorkerSkill:
    """
    Create or update the single baseline skill row for a worker.

    Exactly one baseline exists per worker (enforced by a partial unique index),
    so this updates in place rather than appending — re-running registration
    must not leave a worker with two baseline vectors, which would double-count
    them in every match run.
    """
    baseline = db.execute(
        select(model.WorkerSkill).where(
            model.WorkerSkill.worker_id == worker_id,
            model.WorkerSkill.skill_type == model.SkillType.BASELINE,
        )
    ).scalar_one_or_none()

    if baseline:
        baseline.title = title
        baseline.description = description
        # Only overwrite a good vector with another good vector. A failed
        # embedding call must not blank out a working one and silently drop the
        # worker out of matching.
        if embedding is not None:
            baseline.embedding = embedding
        baseline.is_active = True
        return baseline

    baseline = model.WorkerSkill(
        worker_id=worker_id,
        skill_type=model.SkillType.BASELINE,
        title=title,
        description=description,
        embedding=embedding,
        is_active=True,
    )
    db.add(baseline)
    return baseline


def upsert_speciality_skill(
    db: Session,
    worker_id: int,
    title: str,
    description: str,
    embedding: list[float] | None,
    scenario_question: str | None = None,
    scenario_answer: str | None = None,
    scenario_score: int | None = None,
) -> model.WorkerSkill:
    """
    Add a verified speciality row, or refresh it if this worker already has one
    under the same title.

    Matched on a case-insensitive title so a worker who re-tests the same niche
    updates that row instead of accumulating near-duplicate vectors — duplicates
    would all surface for the same query and crowd out other workers.

    Every other skill row is left untouched. That is the point of the add-skill
    flow: a new niche costs exactly one new embedding, not a full re-embed of a
    profile whose vectors already match well.
    """
    normalised = (title or "").strip()
    if not normalised:
        raise ValueError("A speciality skill requires a title.")

    existing = None
    for skill in db.execute(
        select(model.WorkerSkill).where(
            model.WorkerSkill.worker_id == worker_id,
            model.WorkerSkill.skill_type == model.SkillType.SPECIALITY,
        )
    ).scalars():
        if (skill.title or "").strip().lower() == normalised.lower():
            existing = skill
            break

    if existing:
        existing.description = description
        if embedding is not None:
            existing.embedding = embedding
        if scenario_question is not None:
            existing.scenario_question = scenario_question
        if scenario_answer is not None:
            existing.scenario_answer = scenario_answer
        if scenario_score is not None:
            existing.scenario_score = scenario_score
        existing.is_active = True
        logger.info(
            "Refreshed existing speciality %r for worker_id=%s.", normalised, worker_id,
        )
        return existing

    skill = model.WorkerSkill(
        worker_id=worker_id,
        skill_type=model.SkillType.SPECIALITY,
        title=normalised,
        description=description,
        embedding=embedding,
        scenario_question=scenario_question,
        scenario_answer=scenario_answer,
        scenario_score=scenario_score,
        is_active=True,
    )
    db.add(skill)
    logger.info("Added new speciality %r for worker_id=%s.", normalised, worker_id)
    return skill


def active_skill_titles(db: Session, worker_id: int) -> list[str]:
    """Titles of a worker's active skills — used to tell the interviewer which
    niches this worker has already proved, so the add-skill flow does not
    re-test something already on file."""
    rows = db.execute(
        select(model.WorkerSkill.title).where(
            model.WorkerSkill.worker_id == worker_id,
            model.WorkerSkill.is_active.is_(True),
        )
    ).scalars()
    return [t for t in rows if t]
