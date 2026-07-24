"""
Worker onboarding router — application state management and admin review.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.database.database import get_db
from src.core.oauth2 import get_current_user
from src.core import model, schema
from src.core.worker_profile_helper import sync_profile_extracted_fields, upsert_worker_expertise
from src.ai.worker_chat_analyser_nvidia import build_fresh_history, INITIAL_GREETING, get_worker_description_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/worker-onboarding", tags=["Worker Onboarding"])

# ── Helpers ───────────────────────────────────────────────────────────────────

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
        sync_profile_extracted_fields(profile, session.profile)

    if profile.job_description:
        try:
            embedding_vec = await get_worker_description_embedding(profile.job_description)
        except Exception as exc:
            logger.error("Failed to embed worker job_description: %s", exc)
            embedding_vec = None

        primary_title = profile.job_category or "General Skill"
        upsert_worker_expertise(db, profile.id, primary_title, profile.job_description, embedding_vec)

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
            sync_profile_extracted_fields(profile, session.profile)

    if profile.job_description:
        try:
            embedding_vec = await get_worker_description_embedding(profile.job_description)
        except Exception as exc:
            logger.error("Failed to embed worker job_description on approve: %s", exc)
            embedding_vec = None

        primary_title = profile.job_category or "General Skill"
        upsert_worker_expertise(db, profile.id, primary_title, profile.job_description, embedding_vec)

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