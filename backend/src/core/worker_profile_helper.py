import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.core import model

logger = logging.getLogger(__name__)

_EXTRACTED_PROFILE_FIELDS = frozenset(
    {
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
        "is_certificate",
        "is_license",
        "is_training",
    }
)


def sync_profile_extracted_fields(
    profile: model.WorkerProfile, extracted: dict
) -> None:
    """Copy extracted profile dict fields directly onto the WorkerProfile ORM object."""
    for field in _EXTRACTED_PROFILE_FIELDS:
        if field in extracted and hasattr(profile, field):
            setattr(profile, field, extracted[field])


def upsert_baseline_skill(
    db: Session,
    worker_id: int,
    title: str,
    description: str,
    embedding: Optional[List[float]] = None,
    certificate: Optional[List[Dict[str, Any]]] = None,
    license: Optional[List[Dict[str, Any]]] = None,
    misc: Optional[List[Dict[str, Any]]] = None,
    is_certificate: Optional[bool] = None,
    is_license: Optional[bool] = None,
    is_training: Optional[bool] = None,
) -> model.WorkerSkill:
    """Create or update the baseline WorkerSkill row for a worker."""
    stmt = select(model.WorkerSkill).where(
        model.WorkerSkill.worker_id == worker_id,
        model.WorkerSkill.skill_type == model.SkillType.BASELINE,
    )
    skill = db.execute(stmt).scalar_one_or_none()

    if skill:
        skill.title = title
        skill.description = description
        if embedding is not None:
            skill.embedding = embedding
        if certificate is not None:
            skill.certificate = certificate
        if license is not None:
            skill.license = license
        if misc is not None:
            skill.misc = misc
        if is_certificate is not None:
            skill.is_certificate = is_certificate
        if is_license is not None:
            skill.is_license = is_license
        if is_training is not None:
            skill.is_training = is_training
    else:
        skill = model.WorkerSkill(
            worker_id=worker_id,
            skill_type=model.SkillType.BASELINE,
            stage="pending_admin_review",
            title=title,
            description=description,
            embedding=embedding,
            certificate=certificate if certificate is not None else [],
            license=license if license is not None else [],
            misc=misc if misc is not None else [],
            is_certificate=is_certificate if is_certificate is not None else False,
            is_license=is_license if is_license is not None else False,
            is_training=is_training if is_training is not None else False,
        )
        db.add(skill)

    return skill


def upsert_speciality_skill(
    db: Session,
    worker_id: int,
    title: str,
    description: str,
    embedding: Optional[List[float]] = None,
    scenario_question: Optional[str] = None,
    scenario_answer: Optional[str] = None,
    scenario_score: Optional[int] = None,
) -> model.WorkerSkill:
    """Add or update a speciality WorkerSkill row."""
    stmt = select(model.WorkerSkill).where(
        model.WorkerSkill.worker_id == worker_id,
        model.WorkerSkill.skill_type == model.SkillType.SPECIALITY,
        model.WorkerSkill.title == title,
    )
    skill = db.execute(stmt).scalar_one_or_none()

    if skill:
        skill.description = description
        if embedding is not None:
            skill.embedding = embedding
        if scenario_question:
            skill.scenario_question = scenario_question
        if scenario_answer:
            skill.scenario_answer = scenario_answer
        if scenario_score is not None:
            skill.scenario_score = scenario_score
    else:
        skill = model.WorkerSkill(
            worker_id=worker_id,
            skill_type=model.SkillType.SPECIALITY,
            stage="complete",
            title=title,
            description=description,
            embedding=embedding,
            scenario_question=scenario_question,
            scenario_answer=scenario_answer,
            scenario_score=scenario_score,
        )
        db.add(skill)

    return skill


def active_skill_titles(db: Session, worker_id: int) -> List[str]:
    """Return all active skill titles for a worker."""
    stmt = select(model.WorkerSkill.title).where(
        model.WorkerSkill.worker_id == worker_id,
        model.WorkerSkill.is_active == True,
    )
    return list(db.execute(stmt).scalars().all())
