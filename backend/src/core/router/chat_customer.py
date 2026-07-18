"""
Dispatch router — AI-powered home-repair booking interview.

Endpoints
---------
  POST /dispatch/session
      Start a brand-new chat session.  Returns the opening greeting and
      the new booking_chat_id so the client can display it immediately.

  POST /dispatch/chat
      Send one customer message and get the AI reply back.

  GET  /dispatch/{booking_chat_id}/history
      Fetch the full conversation so far (client-safe subset only).

  GET  /dispatch/{booking_chat_id}/summary
      Fetch the structured extraction result once the session is complete.
"""
import logging
import os
import requests
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from src.database.database import get_db
from src.core.oauth2 import get_current_user
# FIX: Explicitly import matching_manager alongside job_manager from core
from src.core import model, schema, job_manager, matching_manager
from src.core.manager import manager

from src.ai.customer_chat_analyser_nvidia import (
    _nvidia_client,
    build_fresh_history,
    count_user_turns,
    extract_final_json,
    INITIAL_GREETING,
    MAX_TURNS,
    MODEL_NAME,
)

router = APIRouter(prefix="/dispatch", tags=["Dispatch"])
match_router = APIRouter(tags=["Dispatch"])
logger = logging.getLogger(__name__)

DEFAULT_SEARCH_RADIUS_METERS = 60_000  # 60 km — hard cutoff


# ── Helper ───────────────────────────────────────────────────────────────────

def _get_own_session(
    booking_chat_id: int,
    db: Session,
    current_user: model.User,
) -> model.BookingChat:
    """Fetch a BookingChat that belongs to the current user; 404 if missing."""
    session = db.execute(
        select(model.BookingChat).where(
            model.BookingChat.id == booking_chat_id,
            model.BookingChat.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )
    return session


def _get_address_from_coords(lat: float, lng: float) -> str:
    """Detects the physical location address text from latitude and longitude coordinates."""
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lng,
        "format": "json",
        "addressdetails": 1
    }
    headers = {
        "User-Agent": "WorkerVerificationApp/1.0 (contact: admin@yourdomain.com)"
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=8.0)
        if response.status_code == 200:
            data = response.json()
            if "display_name" in data:
                return data["display_name"]
            logger.error("[Geocode Error] 'display_name' field missing in JSON response")
        else:
            logger.error(f"[Geocode Error] Server responded with code: {response.status_code}")
    except Exception as e:
        logger.error(f"[Geocode Exception] Network failure details: {e}")
        
    return f"Location ({lat}, {lng})"


def _fetch_nvidia_embedding(job_desc: str) -> list[float]:
    """Requests a vector embedding from the Nvidia NIM API for a given job description."""
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        logger.error("NVIDIA_API_KEY environment variable is missing.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Embedding configuration error."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    nvidia_payload = {
        "model": "nvidia/nv-embed-v1",
        "input": [job_desc],
        "input_type": "query",
        "encoding_format": "float"
    }

    try:
        logger.info("Requesting embedding from Nvidia NIM...")
        response = requests.post(
            "https://integrate.api.nvidia.com/v1/embeddings",
            headers=headers, 
            json=nvidia_payload, 
            timeout=20.0
        )
        if response.status_code == 200:
            return response.json()["data"][0]["embedding"]
        else:
            logger.error(f"Nvidia API error: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Nvidia API error: {response.status_code}"
            )
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to connect to Nvidia API: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to Nvidia API: {e}"
        )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/session",
    response_model=schema.SessionStartOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new dispatch chat session",
)
def start_session(
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    chat_session = model.BookingChat(
        user_id=current_user.id,
        history=build_fresh_history(),
        is_complete=False,
    )
    db.add(chat_session)

    try:
        db.commit()
        db.refresh(chat_session)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat session.",
        )

    return {
        "booking_chat_id": chat_session.id,
        "ai_response": INITIAL_GREETING,
        "turns_remaining": MAX_TURNS,
    }


@router.post(
    "/chat",
    response_model=schema.ChatMessageOut,
    summary="Send a customer message and receive an AI reply",
)
def dispatch_chat(
    payload: schema.ChatMessageIn,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    if payload.booking_chat_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="booking_chat_id must be a positive integer. Call POST /dispatch/session first.",
        )

    chat_session = _get_own_session(payload.booking_chat_id, db, current_user)

    if chat_session.is_complete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This chat session is already completed. Start a new session.",
        )

    updated_history = list(chat_session.history)
    updated_history.append({"role": "user", "content": payload.message})
    user_turn_count = count_user_turns(updated_history)

    try:
        response = _nvidia_client.chat.completions.create(
            model=MODEL_NAME,
            messages=updated_history,
            temperature=0.0,
            max_tokens=512,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"NVIDIA NIM inference error: {exc}",
        )

    ai_message: str = response.choices[0].message.content.strip()
    force_complete = user_turn_count >= MAX_TURNS
    is_complete = "[COMPLETE]" in ai_message or force_complete

    if force_complete and "[COMPLETE]" not in ai_message:
        ai_message += " [COMPLETE]"

    updated_history.append({"role": "assistant", "content": ai_message})
    chat_session.history = updated_history
    display_message = ai_message.replace("[COMPLETE]", "").strip()

    categories_to_return: list[dict] = []
    tags_to_return: list[str] = []
    job_found: bool = False
    custom_category_flag: bool = False

    if is_complete:
        chat_session.is_complete = True
        try:
            structured = extract_final_json(chat_session.history, MODEL_NAME)
            chat_session.categories = [c.model_dump() for c in structured.categories]
            chat_session.problem_description = structured.problem_description
            chat_session.is_job_request = structured.is_job_request

            categories_to_return = chat_session.categories
            tags_to_return = sorted({tag for c in structured.categories for tag in c.tags})
            job_found = structured.is_job_request
            custom_category_flag = any(c.is_custom_category for c in structured.categories)
        except Exception as extraction_err:
            chat_session.categories = []
            chat_session.problem_description = ""
            chat_session.is_job_request = False
            logger.error(f"[Dispatch] Extraction failure for booking_chat_id={chat_session.id}: {extraction_err}")

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database write failure.",
        )

    return {
        "booking_chat_id": chat_session.id,
        "ai_response": display_message,
        "is_complete": chat_session.is_complete,
        "current_tags": tags_to_return,
        "is_job_request": job_found,
        "is_custom_category": custom_category_flag,
        "turns_used": user_turn_count,
        "turns_remaining": max(0, MAX_TURNS - user_turn_count),
        "problem_description": chat_session.problem_description,
        "categories": categories_to_return
    }


@router.post(
    "/{booking_chat_id}/complete",
    summary="Complete the AI chat, write core records, invoke engine matching, and alert workers",
)
async def complete_customer_chat(
    booking_chat_id: int, 
    payload: schema.CompleteChatIn, 
    db: Session = Depends(get_db), 
    current_user: model.User = Depends(get_current_user)
):
    logger.info(f"Starting completion pipeline for booking_chat_id: {booking_chat_id}")
    
    lng = payload.location.longitude
    lat = payload.location.latitude
    wkt_point = f"POINT({lng} {lat})"

    chat_session = _get_own_session(booking_chat_id, db, current_user)
    if not chat_session.is_complete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot process summary. The AI chat session is not complete yet."
        )
    
    job_desc = payload.edited_description.strip()
    if not job_desc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description is missing. Cannot generate vector profile."
        )

    embedding_vector = _fetch_nvidia_embedding(job_desc)
        
    customer_fields = {
        "is_complete": getattr(chat_session, "is_complete", False),
        "is_job_request": getattr(chat_session, "is_job_request", False),
        "categories": getattr(chat_session, "categories", []), 
        "problem_description": job_desc
    }
    address_text = _get_address_from_coords(lat, lng)

    job_fields = {
        "title": payload.title,
        "description": job_desc,
        "status": payload.status,
        "is_job_request": getattr(chat_session, "is_job_request", True),
        "categories": getattr(chat_session, "categories", []),
        "contact_name": payload.contact_name,
        "contact_phone": payload.contact_phone,
        "mode": payload.mode,
        "attachments": payload.attachments,
        "latitude": lat,
        "longitude": lng,
        "location": wkt_point,
        "description_vector": embedding_vector,
        "address_text": address_text
    }

    try:
        job_manager.upsert_chat_data(db, booking_chat_id, current_user.id, customer_fields)
        # FIX / OPTIMIZATION: Capture the job row returned directly from your upsert tool
        job_data = job_manager.upsert_job(db, booking_chat_id, current_user.id, job_fields)
    except Exception as e:
        db.rollback()
        logger.error(f"Core entity persistence failed: {e}")
        raise HTTPException(status_code=500, detail="Database update failed.")
    
    # Fallback query only if upsert_job does not return the model object instance
    if not job_data:
        job_data = db.execute(
            select(model.Job).where(model.Job.booking_chat_id == booking_chat_id)
        ).scalar_one_or_none()

    if not job_data:
        db.rollback()
        raise HTTPException(status_code=500, detail="Job processing lookup failed after setup.")
    
    # FIX: Correctly routed directly to matching_manager as an independent module dependency
    try:
        matching_result = matching_manager.create_matches_for_job(
            db=db,
            job_id=job_data.id,
            query_vector=embedding_vector,
            customer_location=wkt_point,
            radius_meters=DEFAULT_SEARCH_RADIUS_METERS
        )
        db.commit()
    except Exception as engine_err:
        db.rollback()
        logger.error(f"Matching Engine execution forced transaction rollback: {engine_err}")
        raise HTTPException(status_code=500, detail="Failed to safely compile and record marketplace matches.")

    job_payload = {
        "booking_chat_id": booking_chat_id, 
        "title": payload.title, 
        "description": job_desc
    }
    
    for worker_chat_id in matching_result.get("worker_chat_ids", []):
        try:
            await manager.send_job_notification(worker_chat_id, job_payload)
        except Exception as ws_err:
            logger.warning(f"Failed live alert broadcast to worker {worker_chat_id}: {ws_err}")

    return {
        "status": "success", 
        "message": f"Job registered. Established {matching_result.get('count', 0)} matches successfully."
    }


@router.get(
    "/{booking_chat_id}/history",
    response_model=schema.ChatHistoryOut,
    summary="Get the full conversation history for a session",
)
def get_history(
    booking_chat_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    chat_session = _get_own_session(booking_chat_id, db, current_user)
    visible_history = [
        {
            "role": msg["role"],
            "content": (
                msg["content"].replace("[COMPLETE]", "").strip()
                if msg["role"] == "assistant"
                else msg["content"]
            ),
        }
        for msg in chat_session.history
        if msg["role"] != "system"
    ]

    return {
        "booking_chat_id":  chat_session.id,
        "history":          visible_history,
        "is_complete":      chat_session.is_complete,
        "turns_used":       count_user_turns(chat_session.history),
        "turns_remaining":  max(0, MAX_TURNS - count_user_turns(chat_session.history)),
    }


@router.get(
    "/{booking_chat_id}/summary",
    response_model=schema.BookingSummaryOut,
    summary="Get the structured extraction result (only available after completion)",
)
def get_booking_summary(
    booking_chat_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    chat_session = _get_own_session(booking_chat_id, db, current_user)

    if not chat_session.is_complete:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session is not yet complete. No summary is available.",
        )

    return {
        "categories":           chat_session.categories           or [],
        "problem_description":  chat_session.problem_description  or "",
        "is_complete":          chat_session.is_complete,
        "is_job_request":       bool(chat_session.is_job_request),
    }


def _extract_primary_category(categories: list[dict]) -> tuple[str | None, bool]:
    if not categories:
        return None, False
    top = categories[0]
    return top.get("category"), bool(top.get("is_custom_category", False))


@match_router.get(
    "/match/{booking_chat_id}/find-help",
    response_model=schema.FindHelpOut,
    summary="Fetch pre-calculated matching workers for a completed job layout from DB",
)
def find_help(
    booking_chat_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    # REMINDER: Verify if model.Job uses customer_id or user_id in your schema
    job_data = db.execute(
        select(model.Job).where(
            model.Job.booking_chat_id == booking_chat_id,
            model.Job.customer_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not job_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No operational job data found for this booking_chat_id.",
        )

    category, is_custom = _extract_primary_category(job_data.categories or [])
    
    stmt = (
        select(model.JobWorkerMatch, model.WorkerProfile, model.User.username)
        .join(model.WorkerProfile, model.WorkerProfile.id == model.JobWorkerMatch.worker_id)
        .join(model.User, model.User.id == model.WorkerProfile.user_id)
        .where(
            model.JobWorkerMatch.job_id == job_data.id,
            model.JobWorkerMatch.is_active == True
        )
        .order_by(model.JobWorkerMatch.match_rank.asc())
    )
    matches = db.execute(stmt).all()

    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching workers found recorded for this job specification.",
        )

    workers = [
        {
            "worker_chat_id": worker.worker_chat_id,
            "username": username,
            "job_category": worker.job_category,
            "category_tag": worker.category_tag,
            "job_description": worker.job_description,
            "match_score": match.match_score,
        }
        for match, worker, username in matches
    ]

    return {
        "matched_by_category": bool(category),
        "category": category,
        "workers": workers,
    }