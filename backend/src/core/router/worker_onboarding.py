"""
Worker onboarding router — application state management and admin review.
"""

import logging
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.database.database import get_db
from src.core.oauth2 import get_current_user
from src.core import model, schema
from src.ai.worker_chat_analyser_nvidia import build_fresh_history, INITIAL_GREETING

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/worker-onboarding", tags=["Worker Onboarding"])

# ── Helpers ───────────────────────────────────────────────────────────────────

async def _generate_description_vector(text: str):
    """
    Asynchronous embed generation via NVIDIA nv-embed-v1 using httpx.
    """
    if not text:
        return None
    try:
        headers = {
            "Authorization": f"Bearer {os.getenv('NVIDIA_API_KEY')}",
            "Content-Type": "application/json",
        }
        nvidia_payload = {
            "model": "nvidia/nv-embed-v1",
            "input": [text],
            "input_type": "passage",
            "encoding_format": "float",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://integrate.api.nvidia.com/v1/embeddings",
                headers=headers,
                json=nvidia_payload,
                timeout=20.0,
            )
            if response.status_code == 200:
                return response.json()["data"][0]["embedding"]
            
            logger.error("NVIDIA embedding error: %s - %s", response.status_code, response.text)
    except Exception as exc:
        logger.error("Failed to embed worker job_description: %s", exc)
    return None

def _sync_profile_data(profile: model.WorkerProfile, extracted: dict):
    """Centralized helper to map extracted AI profile data to the DB model."""
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

def _get_own_worker_profile(user_id: int, db: Session) -> model.WorkerProfile | None:
    return db.execute(
        select(model.WorkerProfile).where(model.WorkerProfile.user_id == user_id)
    ).scalar_one_or_none()

def _require_worker_profile(user_id: int, db: Session) -> model.WorkerProfile:
    profile = _get_own_worker_profile(user_id, db)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker profile not found. Initialize your application first.",
        )
    return profile

def _is_admin(user: model.User) -> bool:
    return any(role.name and role.name.lower() == "admin" for role in user.roles)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/initialize",
    response_model=schema.InitializeWorkerAppOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a WorkerProfile record and start an interview session",
)
def initialize_worker_application(
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    existing = _get_own_worker_profile(current_user.id, db)
    if existing:
        return existing

    worker_role = db.query(model.Role).filter(model.Role.name.ilike("worker")).first()
    if not worker_role:
        worker_role = model.Role(name="worker")
        db.add(worker_role)
        db.flush()

    if not any(role.name and role.name.lower() == "worker" for role in current_user.roles):
        current_user.roles.append(worker_role)

    initial_history = build_fresh_history()
    initial_history.append({"role": "assistant", "content": INITIAL_GREETING})

    interview_session = model.WorkerInterviewSession(
        user_id=current_user.id,
        history=initial_history,
        stage="interviewing",
        is_complete=False,
        is_rejected=False,
    )
    db.add(interview_session)
    db.flush()

    worker_profile = model.WorkerProfile(
        user_id=current_user.id,
        worker_chat_id=interview_session.id,
        stage="interviewing",
        is_complete=False,
        is_rejected=False,
        job_category="",
        category_tag="",
        specialities=[],
        specialized_tools_or_equipment=[],
        years_experience=0,
        job_description="",
        scenario_score=0,
    )
    db.add(worker_profile)

    try:
        db.commit()
        db.refresh(worker_profile)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize worker application.",
        )

    return worker_profile


@router.post(
    "/submit",
    response_model=schema.SubmitWorkerAppOut,
    summary="Submit the worker application for admin review",
)
async def submit_worker_application(
    payload: schema.SubmitWorkerAppIn,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    profile = _require_worker_profile(current_user.id, db)

    if profile.is_complete or profile.is_rejected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application is already completed or rejected.",
        )

    profile.stage = "pending_admin_review"
    profile.phone_number = payload.phone_number
    profile.address_text = payload.address_text
    
    if payload.latitude is not None and payload.longitude is not None:
        profile.latitude = payload.latitude
        profile.longitude = payload.longitude
        profile.location = f"POINT({payload.longitude} {payload.latitude})"

    # Fetch latest valid profile session directly utilizing sorting
    stmt = select(model.WorkerInterviewSession).where(
        model.WorkerInterviewSession.user_id == current_user.id,
        model.WorkerInterviewSession.profile.isnot(None)
    ).order_by(model.WorkerInterviewSession.id.desc())
    
    session = db.execute(stmt).scalars().first()

    if session and session.profile:
        _sync_profile_data(profile, session.profile)

    # Handle Vector Embedding asynchronously
    if profile.job_description:
        embedding_vec = await _generate_description_vector(profile.job_description)
        primary_title = profile.job_category or "General Skill"
        
        db_expertise = db.query(model.WorkerExpertise).filter(
            model.WorkerExpertise.worker_id == profile.id,
            model.WorkerExpertise.title == primary_title
        ).first()

        if db_expertise:
            db_expertise.description = profile.job_description
            db_expertise.embedding = embedding_vec
            db_expertise.is_active = True
        else:
            db_expertise = model.WorkerExpertise(
                worker_id=profile.id,
                title=primary_title,
                description=profile.job_description,
                embedding=embedding_vec,
                is_active=True
            )
            db.add(db_expertise)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit application.",
        )

    return {
        "worker_id": profile.id,
        "stage": profile.stage,
        "message": "Application submitted for admin review.",
    }


@router.get(
    "/my-status",
    response_model=schema.WorkerAppStatusOut,
    summary="Get the current user's worker application status",
)
def get_my_application_status(
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    return _require_worker_profile(current_user.id, db)


@router.get(
    "/admin/applications",
    response_model=list[schema.AdminPendingAppOut],
    summary="Admin-only: list all worker applications pending review",
)
def list_pending_applications(
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )

    # Optimized to prevent N+1 Queries
    stmt = (
        select(model.WorkerProfile, model.User, model.WorkerInterviewSession)
        .join(model.User, model.WorkerProfile.user_id == model.User.id)
        .outerjoin(model.WorkerInterviewSession, model.WorkerProfile.worker_chat_id == model.WorkerInterviewSession.id)
        .where(
            model.WorkerProfile.stage == "pending_admin_review",
            model.WorkerProfile.is_complete == False
        )
        .order_by(model.WorkerProfile.id.desc())
    )

    results = db.execute(stmt).all()
    applications = []
    
    for profile, user, session in results:
        # Dictionary unpacking safely merges objects for the Pydantic model
        app_data = {
            **profile.__dict__,
            "username": user.username,
            "email": user.email,
            "firstName": user.firstName,
            "lastName": user.lastName,
            "history": session.history if session else [],
            "profile": session.profile if session else None,
        }
        applications.append(app_data)

    return applications


@router.post(
    "/admin/applications/{worker_id}/approve",
    summary="Admin-only: approve a worker application",
)
async def approve_worker_application(
    worker_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")

    profile = db.query(model.WorkerProfile).filter(model.WorkerProfile.id == worker_id).first()

    if not profile or profile.stage != "pending_admin_review":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valid pending application not found.")

    profile.is_complete = True
    profile.stage = "approved"
    profile.is_rejected = False
    profile.rejection_reason = None

    if not profile.job_category and profile.worker_chat_id:
        session = db.execute(select(model.WorkerInterviewSession).where(model.WorkerInterviewSession.id == profile.worker_chat_id)).scalar_one_or_none()
        if session and session.profile:
            _sync_profile_data(profile, session.profile)

    if profile.job_description:
        existing_expertise = db.query(model.WorkerExpertise).filter(
            model.WorkerExpertise.worker_id == profile.id,
            model.WorkerExpertise.embedding.isnot(None)
        ).first()

        if not existing_expertise:
            embedding_vec = await _generate_description_vector(profile.job_description)
            db_expertise = model.WorkerExpertise(
                worker_id=profile.id,
                title=profile.job_category or "General Skill",
                description=profile.job_description,
                embedding=embedding_vec,
                is_active=True
            )
            db.add(db_expertise)

    user = db.query(model.User).filter(model.User.id == profile.user_id).first()
    worker_role = db.query(model.Role).filter(model.Role.name.ilike("worker")).first()
    if user and worker_role and worker_role not in user.roles:
        user.roles.append(worker_role)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to approve application.")

    return {"message": "Application approved successfully.", "worker_id": worker_id}


@router.post(
    "/admin/applications/{worker_id}/reject",
    summary="Admin-only: reject a worker application with a reason",
)
def reject_worker_application(
    worker_id: int,
    payload: schema.RejectWorkerIn,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")

    profile = db.query(model.WorkerProfile).filter(model.WorkerProfile.id == worker_id).first()

    if not profile or profile.stage != "pending_admin_review":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valid pending application not found.")

    profile.is_complete = False
    profile.is_rejected = True
    profile.rejection_reason = payload.reason
    profile.stage = "rejected"

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reject application.")

    return {"message": "Application rejected.", "worker_id": worker_id, "reason": payload.reason}


@router.patch(
    "/my-profile",
    response_model=schema.UpdateWorkerProfileOut,
    summary="Update the current user's worker profile fields",
)
def update_my_worker_profile(
    payload: schema.UpdateWorkerProfileIn,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    profile = _require_worker_profile(current_user.id, db)
    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(profile, field):
            setattr(profile, field, value)

    try:
        db.commit()
        db.refresh(profile)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update worker profile.")

    return {**profile.__dict__, "message": "Profile updated successfully."}