"""
Worker onboarding router — application state management and admin review.

Endpoints
---------
  POST /worker-onboarding/initialize
      Create a WorkerProfile record for the current user with default
      applicant states, and start a WorkerInterviewSession. Returns the
      new worker_chat_id so the client can begin the AI interview.

  POST /worker-onboarding/submit
      Update the current user's WorkerProfile stage to 'pending_admin_review'
      and persist phone/address/location data collected during onboarding.

  GET  /worker-onboarding/my-status
      Fetch the current user's WorkerProfile and basic interview session info.

  GET  /admin/worker-applications
      Admin-only. List all WorkerProfile records where stage == 'pending_admin_review'
      and is_complete == False, joined with user info and chat history.

  POST /admin/worker-applications/{worker_id}/approve
      Admin-only. Mark the application as approved (is_complete=True, stage='approved').

  POST /admin/worker-applications/{worker_id}/reject
      Admin-only. Mark the application as rejected (is_rejected=True) and
      save the admin-provided reason.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.database.database import get_db
from src.core.oauth2 import get_current_user
from src.core import model, schema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/worker-onboarding", tags=["Worker Onboarding"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_own_worker_profile(
    user_id: int,
    db: Session,
) -> model.WorkerProfile | None:
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
    return any(
        role.name and role.name.lower() == "admin" for role in user.roles
    )


# ── 1. Initialize Application ─────────────────────────────────────────────────

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
        return {
            "worker_id": existing.id,
            "user_id": existing.user_id,
            "stage": existing.stage,
            "is_complete": existing.is_complete,
            "is_rejected": existing.is_rejected,
            "worker_chat_id": existing.worker_chat_id,
        }

    worker_role = (
        db.query(model.Role)
        .filter(model.Role.name.ilike("worker"))
        .first()
    )
    if not worker_role:
        worker_role = model.Role(name="worker")
        db.add(worker_role)
        db.flush()

    already_worker = any(
        role.name and role.name.lower() == "worker" for role in current_user.roles
    )
    if not already_worker:
        current_user.roles.append(worker_role)

    interview_session = model.WorkerInterviewSession(
        user_id=current_user.id,
        history=[],
        stage="interviewing",
        is_complete=False,
        is_rejected=False,
    )
    db.add(interview_session)
    db.flush()

    worker_profile = model.WorkerProfile(
        user_id=current_user.id,
        worker_chat_id=interview_session.id,
        stage="pending_interview",
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

    return {
        "worker_id": worker_profile.id,
        "user_id": worker_profile.user_id,
        "stage": worker_profile.stage,
        "is_complete": worker_profile.is_complete,
        "is_rejected": worker_profile.is_rejected,
        "worker_chat_id": worker_profile.worker_chat_id,
    }


# ── 2. Submit Application ─────────────────────────────────────────────────────

@router.post(
    "/submit",
    response_model=schema.SubmitWorkerAppOut,
    summary="Submit the worker application for admin review",
)
def submit_worker_application(
    payload: schema.SubmitWorkerAppIn,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    profile = _require_worker_profile(current_user.id, db)

    if profile.is_complete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application is already complete.",
        )

    if profile.is_rejected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application has been rejected.",
        )

    profile.stage = "pending_admin_review"
    profile.phone_number = payload.phone_number
    profile.address_text = payload.address_text
    profile.latitude = payload.latitude
    profile.longitude = payload.longitude

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


# ── 3. My Application Status ──────────────────────────────────────────────────

@router.get(
    "/my-status",
    response_model=schema.WorkerAppStatusOut,
    summary="Get the current user's worker application status",
)
def get_my_application_status(
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    profile = _require_worker_profile(current_user.id, db)

    return {
        "worker_id": profile.id,
        "stage": profile.stage,
        "is_complete": profile.is_complete,
        "is_rejected": profile.is_rejected,
        "rejection_reason": profile.rejection_reason,
        "job_category": profile.job_category,
        "category_tag": profile.category_tag,
        "specialities": profile.specialities,
        "years_experience": profile.years_experience,
        "worker_chat_id": profile.worker_chat_id,
        "phone_number": profile.phone_number,
        "address_text": profile.address_text,
    }


# ── 4. Admin: List Pending Applications ──────────────────────────────────────

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

    stmt = (
        select(model.WorkerProfile, model.User)
        .join(model.User, model.WorkerProfile.user_id == model.User.id)
        .where(
            model.WorkerProfile.stage == "pending_admin_review",
            model.WorkerProfile.is_complete == False,  # noqa: E712
        )
        .order_by(model.WorkerProfile.id.desc())
    )

    results = db.execute(stmt).all()
    applications = []
    for profile, user in results:
        session = db.execute(
            select(model.WorkerInterviewSession).where(
                model.WorkerInterviewSession.id == profile.worker_chat_id
            )
        ).scalar_one_or_none()

        applications.append({
            "id": profile.id,
            "user_id": profile.user_id,
            "username": user.username,
            "email": user.email,
            "firstName": user.firstName,
            "lastName": user.lastName,
            "stage": profile.stage,
            "is_complete": profile.is_complete,
            "is_rejected": profile.is_rejected,
            "rejection_reason": profile.rejection_reason,
            "job_category": profile.job_category,
            "category_tag": profile.category_tag,
            "specialities": profile.specialities,
            "years_experience": profile.years_experience,
            "worker_chat_id": profile.worker_chat_id,
            "phone_number": profile.phone_number,
            "address_text": profile.address_text,
            "history": session.history if session else [],
            "profile": session.profile if session else None,
        })

    return applications


# ── 5. Admin: Approve Application ─────────────────────────────────────────────

@router.post(
    "/admin/applications/{worker_id}/approve",
    summary="Admin-only: approve a worker application",
)
def approve_worker_application(
    worker_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )

    profile = db.query(model.WorkerProfile).filter(
        model.WorkerProfile.id == worker_id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker application not found.",
        )

    if profile.stage != "pending_admin_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Application is in stage '{profile.stage}', not pending review.",
        )

    profile.is_complete = True
    profile.stage = "approved"
    profile.is_rejected = False
    profile.rejection_reason = None

    user = db.query(model.User).filter(model.User.id == profile.user_id).first()
    if user:
        worker_role = (
            db.query(model.Role)
            .filter(model.Role.name.ilike("worker"))
            .first()
        )
        if worker_role and worker_role not in user.roles:
            user.roles.append(worker_role)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve application.",
        )

    return {"message": "Application approved successfully.", "worker_id": worker_id}


# ── 6. Admin: Reject Application ──────────────────────────────────────────────

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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )

    profile = db.query(model.WorkerProfile).filter(
        model.WorkerProfile.id == worker_id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker application not found.",
        )

    if profile.stage != "pending_admin_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Application is in stage '{profile.stage}', not pending review.",
        )

    profile.is_complete = False
    profile.is_rejected = True
    profile.rejection_reason = payload.reason
    profile.stage = "rejected"

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject application.",
        )

    return {"message": "Application rejected.", "worker_id": worker_id, "reason": payload.reason}


# ── 7. Update Worker Profile ──────────────────────────────────────────────────

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update worker profile.",
        )

    return {
        "worker_id": profile.id,
        "job_category": profile.job_category,
        "category_tag": profile.category_tag,
        "specialities": profile.specialities,
        "years_experience": profile.years_experience,
        "license_or_certification": profile.license_or_certification,
        "job_description": profile.job_description,
        "emergency_available": profile.emergency_available,
        "phone_number": profile.phone_number,
        "address_text": profile.address_text,
        "message": "Profile updated successfully.",
    }
