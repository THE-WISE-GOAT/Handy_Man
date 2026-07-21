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
import os
import requests
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.database.database import get_db
from src.core.oauth2 import get_current_user
from src.core import model, schema
from src.ai.worker_chat_analyser_nvidia import build_fresh_history, INITIAL_GREETING

logger = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_description_vector(text: str):
    """
    Embed a worker's job_description via NVIDIA nv-embed-v1 so it can be
    cosine-matched against customer job vectors in the matching engine.
    Returns the embedding list, or None if embedding is unavailable.
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
        response = requests.post(
            "https://integrate.api.nvidia.com/v1/embeddings",
            headers=headers,
            json=nvidia_payload,
            timeout=20.0,
        )
        if response.status_code == 200:
            return response.json()["data"][0]["embedding"]
        logger.error(
            "NVIDIA embedding error in worker onboarding: %s - %s",
            response.status_code, response.text,
        )
    except Exception as exc:
        logger.error("Failed to embed worker job_description: %s", exc)
    return None


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

    # Build the proper AI history and inject the first question so it saves to the DB immediately
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
        stage="interviewing",  # Align the profile stage with the chat stage
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

    # ── Carry the AI-extracted interview profile into the WorkerProfile ──
    # The interview router stores the validated WorkerProfileSchema dict on
    # WorkerInterviewSession.profile. The admin review and the matching
    # engine both read the WorkerProfile columns, so we MUST copy the
    # extracted fields across here — otherwise an approved worker keeps an
    # empty profile (all "None") and the job matcher finds no vector.
    session = db.execute(
        select(model.WorkerInterviewSession).where(
            model.WorkerInterviewSession.id == payload.worker_chat_id,
            model.WorkerInterviewSession.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    # Guard against the dual-session drift: if the session linked to
    # worker_chat_id has no extracted profile, fall back to the user's
    # COMPLETED session (the one that actually holds the data).
    if not (session and session.profile):
        session = db.execute(
            select(model.WorkerInterviewSession)
            .where(
                model.WorkerInterviewSession.user_id == current_user.id,
                model.WorkerInterviewSession.is_complete.is_(True),
                model.WorkerInterviewSession.profile.isnot(None),
            )
            .order_by(model.WorkerInterviewSession.id.desc())
        ).scalars().first()

    if session and session.profile:
        extracted = session.profile
        profile.job_category = extracted.get("job_category", profile.job_category)
        profile.category_tag = extracted.get("category_tag", profile.category_tag)
        profile.is_custom_category = extracted.get("is_custom_category", profile.is_custom_category)
        profile.specialities = extracted.get("specialities", []) or []
        profile.years_experience = extracted.get("years_experience", 0) or 0
        profile.license_or_certification = extracted.get("license_or_certification")
        profile.specialized_tools_or_equipment = (
            extracted.get("specialized_tools_or_equipment", []) or []
        )
        profile.job_description = extracted.get("job_description", "") or ""
        profile.emergency_available = extracted.get("emergency_available", False) or False
        profile.has_verified_specialty = extracted.get("has_verified_specialty", False) or False
        profile.scenario_passed = extracted.get("scenario_passed", False) or False
        profile.scenario_score = extracted.get("scenario_score", 0) or 0

    # ── Generate the semantic embedding + geolocation ──
    # The matching engine (chat_customer.find_help / matching_manager) only
    # considers workers whose description_vector AND location are non-null
    # and is_complete=True. Without these, an approved worker never
    # receives routed jobs. The embedding is derived from job_description,
    # which the extraction step produced above.
    if payload.latitude is not None and payload.longitude is not None:
        profile.latitude = payload.latitude
        profile.longitude = payload.longitude
        profile.location = f"POINT({payload.longitude} {payload.latitude})"

    if profile.job_description:
        profile.description_vector = _generate_description_vector(
            profile.job_description
        )

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
        "is_custom_category": profile.is_custom_category,
        "specialities": profile.specialities,
        "specialized_tools_or_equipment": profile.specialized_tools_or_equipment,
        "years_experience": profile.years_experience,
        "license_or_certification": profile.license_or_certification,
        "job_description": profile.job_description,
        "emergency_available": profile.emergency_available,
        "has_verified_specialty": profile.has_verified_specialty,
        "scenario_passed": profile.scenario_passed,
        "scenario_score": profile.scenario_score,
        "worker_chat_id": profile.worker_chat_id,
        "phone_number": profile.phone_number,
        "address_text": profile.address_text,
        "latitude": profile.latitude,
        "longitude": profile.longitude,
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
        if not (session and (session.history or session.profile)):
            session = db.execute(
                select(model.WorkerInterviewSession)
                .where(
                    model.WorkerInterviewSession.user_id == profile.user_id,
                    model.WorkerInterviewSession.is_complete.is_(True),
                )
                .order_by(model.WorkerInterviewSession.id.desc())
            ).scalars().first()

        raw_history = (session.history if session and session.history else []) or []
        raw_profile = (session.profile if session and session.profile else None)

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
            "is_custom_category": profile.is_custom_category,
            "specialities": profile.specialities,
            "years_experience": profile.years_experience,
            "license_or_certification": profile.license_or_certification,
            "job_description": profile.job_description,
            "emergency_available": profile.emergency_available,
            "worker_chat_id": profile.worker_chat_id,
            "phone_number": profile.phone_number,
            "address_text": profile.address_text,
            "history": raw_history,
            "profile": raw_profile,
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

    # ── Backstop: ensure the AI-extracted profile is present ──
    # If the approved WorkerProfile still has empty core fields (e.g. the
    # submit step ran before extraction was copied, or an edge-case flow),
    # pull them from the linked interview session so the worker's dashboard
    # and the matching engine both see the real details.
    if not profile.job_category and profile.worker_chat_id:
        session = db.execute(
            select(model.WorkerInterviewSession).where(
                model.WorkerInterviewSession.id == profile.worker_chat_id
            )
        ).scalar_one_or_none()
        if session and session.profile:
            extracted = session.profile
            profile.job_category = extracted.get("job_category", profile.job_category)
            profile.category_tag = extracted.get("category_tag", profile.category_tag)
            profile.is_custom_category = extracted.get("is_custom_category", profile.is_custom_category)
            profile.specialities = extracted.get("specialities", []) or []
            profile.years_experience = extracted.get("years_experience", 0) or 0
            profile.license_or_certification = extracted.get("license_or_certification")
            profile.specialized_tools_or_equipment = (
                extracted.get("specialized_tools_or_equipment", []) or []
            )
            profile.job_description = extracted.get("job_description", "") or ""
            profile.emergency_available = extracted.get("emergency_available", False) or False
            profile.has_verified_specialty = extracted.get("has_verified_specialty", False) or False
            profile.scenario_passed = extracted.get("scenario_passed", False) or False
            profile.scenario_score = extracted.get("scenario_score", 0) or 0

    # ── Generate the semantic embedding on approval ──
    # The matching engine (chat_customer.find_help) only routes jobs to
    # workers whose description_vector is non-null. If submit didn't persist
    # one (e.g. embedding API was down), (re)generate it now from the
    # job_description so the approved worker actually receives jobs.
    if profile.job_description and profile.description_vector is None:
        profile.description_vector = _generate_description_vector(profile.job_description)

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