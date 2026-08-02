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
from src.core.worker_profile_helper import sync_profile_extracted_fields, upsert_baseline_skill
from src.ai.worker_chat_analyser_nvidia import build_fresh_history, INITIAL_GREETING, get_worker_description_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/worker-onboarding", tags=["Worker Onboarding"])

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_own_worker_profile(user_id: int, db: Session) -> model.WorkerProfile | None:
    return db.execute(
        select(model.WorkerProfile)
        .where(model.WorkerProfile.user_id == user_id)
        .order_by(model.WorkerProfile.id.desc())
    ).scalars().first()

def _require_worker_profile(user_id: int, db: Session) -> model.WorkerProfile:
    profile = _get_own_worker_profile(user_id, db)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker profile not found. Initialize your application first.",
        )
    return profile

def require_approved_worker(current_user: model.User = Depends(get_current_user), db: Session = Depends(get_db)) -> model.WorkerProfile:
    profile = _get_own_worker_profile(current_user.id, db)
    if not profile or profile.stage != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Worker application not approved.",
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
        # This path has only the composed job_description to work with (it never
        # ran the two-layer split), so it becomes the baseline. upsert_baseline_skill
        # updates in place, so re-submitting cannot create a second baseline, and a
        # failed embedding leaves any existing good vector alone.
        upsert_baseline_skill(db, profile.id, primary_title, profile.job_description, embedding_vec)

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
    profile = _get_own_worker_profile(current_user.id, db)
    if not profile:
        has_worker_role = any(
            r.name and r.name.lower() == "worker"
            for r in current_user.roles
        )
        if has_worker_role:
            session = model.WorkerInterviewSession(
                user_id=current_user.id,
                history=[],
                stage="approved",
                is_complete=True,
                is_rejected=False,
            )
            db.add(session)
            db.flush()

            profile = model.WorkerProfile(
                user_id=current_user.id,
                worker_chat_id=session.id,
                stage="approved",
                is_complete=True,
                is_rejected=False,
                job_category="general",
                category_tag="general",
                specialities=[],
                specialized_tools_or_equipment=[],
                years_experience=0,
                license_or_certification=None,
                job_description="",
                scenario_score=0,
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
            return profile
        return _require_worker_profile(current_user.id, db)
    return profile


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

    # Fetch strictly based on WorkerSkill stage
    stmt = (
        select(model.WorkerProfile, model.User, model.WorkerInterviewSession, model.WorkerSkill)
        .join(model.User, model.WorkerProfile.user_id == model.User.id)
        .outerjoin(
            model.WorkerInterviewSession, 
            model.WorkerProfile.worker_chat_id == model.WorkerInterviewSession.id
        )
        .join(model.WorkerSkill, model.WorkerProfile.id == model.WorkerSkill.worker_id)
        .where(
            model.WorkerSkill.stage == "pending_admin_review" # Strict filter on WorkerSkill
        )
        .order_by(model.WorkerSkill.updated_at.desc())
    )

    results = db.execute(stmt).all()
    applications = []
    
    for profile, user, session, skill in results:
        app_data = {
            **profile.__dict__,
            # Override WorkerProfile stage with WorkerSkill stage
            "stage": skill.stage,
            "skill_id": skill.id,
            "skill_title": skill.title,
            "skill_type": skill.skill_type,
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
    "/admin/applications/{skill_id}/approve",
    status_code=status.HTTP_200_OK,
    summary="Admin-only: Approve a worker application skill",
)
def approve_worker_application(
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )

    # 1. Locate the specific WorkerSkill being approved
    skill = db.scalar(select(model.WorkerSkill).where(model.WorkerSkill.id == skill_id))
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker skill entry {skill_id} not found.",
        )

    # 2. Update the skill stage
    skill.stage = "complete"
    skill.rejection_reason = None

    # 3. Locate and update the parent WorkerProfile
    profile = db.scalar(select(model.WorkerProfile).where(model.WorkerProfile.id == skill.worker_id))
    if profile:
        profile.stage = "approved"
        profile.is_complete = True
        profile.is_rejected = False
        profile.rejection_reason = None

    db.commit()
    if profile:
        db.refresh(profile)
    db.refresh(skill)

    return {"message": f"Worker application skill {skill_id} approved successfully."}


@router.post(
    "/admin/applications/{skill_id}/reject",
    status_code=status.HTTP_200_OK,
    summary="Admin-only: Reject a worker application skill",
)
def reject_worker_application(
    skill_id: int,
    payload: schema.RejectWorkerIn,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )

    skill = db.scalar(select(model.WorkerSkill).where(model.WorkerSkill.id == skill_id))
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker skill entry {skill_id} not found.",
        )

    skill.stage = "rejected"
    skill.rejection_reason = payload.reason

    profile = db.scalar(select(model.WorkerProfile).where(model.WorkerProfile.id == skill.worker_id))
    if profile:
        profile.stage = "rejected"
        profile.is_rejected = True
        profile.rejection_reason = payload.reason

    db.commit()
    if profile:
        db.refresh(profile)
    db.refresh(skill)

    return {"message": f"Worker application skill {skill_id} rejected."}

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

    return {**profile.__dict__, "worker_id": profile.id, "message": "Profile updated successfully."}