from sqlalchemy.orm import Session
from src.core import model


def sync_profile_extracted_fields(profile: model.WorkerProfile, extracted: dict):
    profile.job_category = extracted.get("job_category", profile.job_category)
    profile.category_tag = extracted.get("category_tag", profile.category_tag)
    profile.is_custom_category = extracted.get("is_custom_category", profile.is_custom_category)
    profile.specialities = extracted.get("specialities", []) or []
    profile.years_experience = extracted.get("years_experience", 0) or 0
    profile.license_or_certification = extracted.get("license_or_certification")
    profile.specialized_tools_or_equipment = extracted.get("specialized_tools_or_equipment", []) or []
    profile.job_description = extracted.get("job_description", "") or ""
    profile.emergency_available = extracted.get("emergency_available", False) or False
    profile.has_verified_specialty = extracted.get("has_verified_specialty", False) or False
    profile.scenario_passed = extracted.get("scenario_passed", False) or False
    profile.scenario_score = extracted.get("scenario_score", 0) or 0


def upsert_worker_expertise(db: Session, worker_id: int, title: str, description: str, embedding: list[float] | None):
    db_expertise = db.query(model.WorkerExpertise).filter(
        model.WorkerExpertise.worker_id == worker_id,
        model.WorkerExpertise.title == title,
    ).first()

    if db_expertise:
        db_expertise.description = description
        db_expertise.embedding = embedding
        db_expertise.is_active = True
    else:
        db_expertise = model.WorkerExpertise(
            worker_id=worker_id,
            title=title,
            description=description,
            embedding=embedding,
            is_active=True,
        )
        db.add(db_expertise)
