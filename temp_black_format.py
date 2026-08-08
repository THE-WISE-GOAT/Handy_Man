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
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from src.database.database import get_db
from src.core.oauth2 import get_current_user
from src.core import model, schema, job_manager, matching_manager
from src.core.manager import manager
import math
from fastapi.concurrency import run_in_threadpool
import json
from typing import Dict, Any

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
match_router = APIRouter(tags=["Matching"])
logger = logging.getLogger(__name__)

DEFAULT_SEARCH_RADIUS_METERS = 600_000


def _get_own_session(
    booking_chat_id: int,
    db: Session,
    current_user: model.User,
) -> model.BookingChat:
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


def _get_booking_or_worker_access(
    booking_chat_id: int,
    db: Session,
    current_user: model.User,
) -> model.BookingChat | None:
    session = db.execute(
        select(model.BookingChat).where(
            model.BookingChat.id == booking_chat_id,
        )
    ).scalar_one_or_none()

    if not session:
        return None

    if session.user_id == current_user.id:
        return session

    job = db.execute(
        select(model.Job).where(
            model.Job.booking_chat_id == booking_chat_id,
            model.Job.worker_id == current_user.id,
        )
    ).scalar_one_or_none()

    if job:
        return session

    matched_job = db.execute(
        select(model.Job).where(model.Job.booking_chat_id == booking_chat_id)
    ).scalar_one_or_none()

    if matched_job:
        worker_profiles = db.execute(
            select(model.WorkerProfile).where(
                model.WorkerProfile.user_id == current_user.id
            )
        ).scalars().all()

        if worker_profiles:
            worker_profile_ids = [profile.id for profile in worker_profiles]
            match = db.execute(
                select(model.JobWorkerMatch).where(
                    model.JobWorkerMatch.job_id == matched_job.id,
                    model.JobWorkerMatch.worker_id.in_(worker_profile_ids),
                    model.JobWorkerMatch.is_active == True,
                )
            ).scalar_one_or_none()

            if match:
                return session

    return None


def _user_display_name(user: model.User) -> str:
    parts = [user.firstName, user.lastName]
    name = " ".join(p for p in parts if p).strip()
    return name or user.username or "User"


def _resolve_booking_chat(
    booking_chat_id: int,
    db: Session,
    current_user: model.User,
) -> model.BookingChat | None:
    session = _get_booking_or_worker_access(booking_chat_id, db, current_user)
    if session is not None:
        return session

    job = db.execute(
        select(model.Job).where(model.Job.id == booking_chat_id)
    ).scalar_one_or_none()

    if not job:
        return None

    is_owner = job.customer_id == current_user.id
    is_assigned_worker = (
        job.worker_id is not None and job.worker_id == current_user.id
    )

    is_matched_worker = False
    if not is_assigned_worker:
        worker_profile = db.execute(
            select(model.WorkerProfile).where(
                model.WorkerProfile.user_id == current_user.id
            )
        ).scalar_one_or_none()
        if worker_profile:
            match = db.execute(
                select(model.JobWorkerMatch).where(
                    model.JobWorkerMatch.job_id == job.id,
                    model.JobWorkerMatch.worker_id == worker_profile.id,
                    model.JobWorkerMatch.is_active == True,
                )
            ).scalar_one_or_none()
            if match:
                is_matched_worker = True

    if not is_owner and not is_assigned_worker and not is_matched_worker:
        return None

    new_chat = model.BookingChat(
        user_id=job.customer_id,
        history=[],
        is_complete=False,
        is_job_request=False,
    )
    db.add(new_chat)
    db.flush()

    job.booking_chat_id = new_chat.id
    db.flush()

    return new_chat


async def _get_address_from_coords(lat: float, lng: float) -> str:
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"lat": lat, "lon": lng, "format": "json", "addressdetails": 1}
    headers = {
        "User-Agent": "WorkerVerificationApp/1.0 (contact: admin@yourdomain.com)"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, params=params, headers=headers, timeout=8.0
            )
            if response.status_code == 200:
                data = response.json()
                if "display_name" in data:
                    return data["display_name"]
                logger.error(
                    "[Geocode Error] 'display_name' field missing in JSON response"
                )
            else:
                logger.error(
                    f"[Geocode Error] Server responded with code: {response.status_code}"
                )
    except Exception as e:
        logger.error(f"[Geocode Exception] Network failure details: {e}")

    return f"Location ({lat}, {lng})"


async def _fetch_nvidia_embedding(job_desc: str) -> list[float]:
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        logger.error("NVIDIA_API_KEY environment variable is missing.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Embedding configuration error.",
        )

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    nvidia_payload = {
        "model": "nvidia/nv-embed-v1",
        "input": [job_desc],
        "input_type": "query",
        "encoding_format": "float",
    }

    try:
        logger.info("Requesting embedding from Nvidia NIM...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://integrate.api.nvidia.com/v1/embeddings",
                headers=headers,
                json=nvidia_payload,
                timeout=20.0,
            )
            if response.status_code == 200:
                return response.json()["data"][0]["embedding"]
            else:
                logger.error(
                    f"Nvidia API error: {response.status_code} - {response.text}"
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Nvidia API error: {response.status_code}",
                )
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to Nvidia API: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to Nvidia API: {e}",
        )


async def _broadcast_notifications(worker_chat_ids: list[int], job_payload: dict):
    for worker_chat_id in worker_chat_ids:
        try:
            await manager.send_worker_notification(worker_chat_id, job_payload)
        except Exception as ws_err:
            logger.warning(
                f"Failed live alert broadcast to worker {worker_chat_id}: {ws_err}"
            )


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
            tags_to_return = sorted(
                {tag for c in structured.categories for tag in c.tags}
            )
            job_found = structured.is_job_request
            custom_category_flag = any(
                c.is_custom_category for c in structured.categories
            )
        except Exception as extraction_err:
            chat_session.categories = []
            chat_session.problem_description = ""
            chat_session.is_job_request = False
            logger.error(
                f"[Dispatch] Extraction failure for booking_chat_id={chat_session.id}: {extraction_err}"
            )

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
        "categories": categories_to_return,
    }


@router.post(
    "/chat/{booking_chat_id}/message",
    response_model=schema.HumanChatMessageOut,
    summary="Send a human message in a booking chat and broadcast to the other party",
)
async def send_human_message(
    booking_chat_id: int,
    payload: schema.HumanChatMessageIn,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    chat_session = _resolve_booking_chat(booking_chat_id, db, current_user)

    if chat_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )

    sender_name = _user_display_name(current_user)

    updated_history = list(chat_session.history)
    updated_history.append(
        {"role": payload.sender, "content": payload.message, "sender_name": sender_name, "sender_id": current_user.id}
    )
    chat_session.history = updated_history

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database write failure.",
        )

    message_payload = {
        "type": "HUMAN_MESSAGE",
        "data": {
            "booking_chat_id": chat_session.id,
            "sender": payload.sender,
            "sender_name": sender_name,
            "sender_id": current_user.id,
            "message": payload.message,
        }
    }

    if payload.sender == "customer":
        job = db.execute(
            select(model.Job).where(model.Job.booking_chat_id == chat_session.id)
        ).scalar_one_or_none()
        if job:
            if job.worker_id:
                worker_session = db.execute(
                    select(model.WorkerInterviewSession).where(
                        model.WorkerInterviewSession.user_id == job.worker_id
                    )
                ).scalar_one_or_none()
                if worker_session:
                    await manager.send_worker_notification(worker_session.id, message_payload)

            matched_profiles = db.execute(
                select(model.WorkerProfile).join(
                    model.JobWorkerMatch,
                    model.JobWorkerMatch.worker_id == model.WorkerProfile.id,
                ).where(
                    model.JobWorkerMatch.job_id == job.id,
                    model.JobWorkerMatch.is_active == True,
                )
            ).scalars().all()
            for profile in matched_profiles:
                if profile.worker_chat_id:
                    await manager.send_worker_notification(profile.worker_chat_id, message_payload)

            await manager.send_worker_notification(
                chat_session.id, message_payload
            )
    elif payload.sender == "worker":
        await manager.send_customer_notification(chat_session.id, message_payload)

    return {
        "booking_chat_id": chat_session.id,
        "message": payload.message,
        "sender": payload.sender,
        "sender_name": sender_name,
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
    chat_session = _resolve_booking_chat(booking_chat_id, db, current_user)

    if chat_session is None:
        return {
            "booking_chat_id": booking_chat_id,
            "history": [],
            "is_complete": False,
            "turns_used": 0,
            "turns_remaining": MAX_TURNS,
        }

    visible_history = [
        {
            "role": msg["role"],
            "content": (
                msg["content"].replace("[COMPLETE]", "").strip()
                if msg["role"] == "assistant"
                else msg["content"]
            ),
            "sender_name": msg.get("sender_name"),
            "sender_id": msg.get("sender_id"),
        }
        for msg in chat_session.history
        if msg["role"] not in ("user", "assistant")
    ]

    return {
        "booking_chat_id": chat_session.id,
        "history": visible_history,
        "is_complete": chat_session.is_complete,
        "turns_used": count_user_turns(chat_session.history),
        "turns_remaining": max(0, MAX_TURNS - count_user_turns(chat_session.history)),
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
        "categories": chat_session.categories or [],
        "problem_description": chat_session.problem_description or "",
        "is_complete": chat_session.is_complete,
        "is_job_request": bool(chat_session.is_job_request),
    }


async def _refine_job_description_with_ai(raw_description: str) -> Dict[str, Any]:
    prompt = f"""
    You are a backend data processor for a service marketplace. Your job is to clean up a customer's raw task description and categorize it.
    
    Output valid JSON strictly matching this schema:
    {{
        "refined_description": "A single, clear, and reliable paragraph describing the physical work required. No headers, no bullet points.",
        "categories": [
            {{
                "category": "Main trade (e.g., plumbing, electrical, cleaning, automotive, moving)",
                "tags": ["specific-task-1", "specific-task-2"],
                "is_custom_category": true
            }}
        ]
    }}
    
    Raw Customer Text: {raw_description}
    """

    try:
        response = await run_in_threadpool(
            lambda: _nvidia_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=300,
                response_format={
                    "type": "json_object"
                },
            )
        )

        content = response.choices[0].message.content.strip()

        if content.startswith("```json"):
            content = content[7:-3]

        return json.loads(content)

    except Exception as e:
        logger.error(
            f"AI description refinement & categorization failed: {e}. Falling back to raw text."
        )
        return {
            "refined_description": raw_description,
            "categories": [
                {
                    "category": "general",
                    "tags": ["manual-entry"],
                    "is_custom_category": True,
                }
            ],
        }


async def _broadcast_customer_bid(booking_chat_id: int, bid_payload: dict):
    """Send a SYSTEM_BID notification to the customer's WebSocket connection."""
    from src.core.manager import manager
    try:
        await manager.send_customer_notification(booking_chat_id, bid_payload)
    except Exception as ws_err:
        logger.warning(f"Failed SYSTEM_BID broadcast to booking {booking_chat_id}: {ws_err}")


@router.post(
    "/{booking_chat_id}/complete",
    summary="Complete the AI chat, write core records, invoke engine matching, and alert workers",
)
async def complete_customer_chat(
    booking_chat_id: int,
    payload: schema.CompleteChatIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    logger.info(f"Starting completion pipeline for booking_chat_id: {booking_chat_id}")

    lng = payload.location.longitude
    lat = payload.location.latitude
    wkt_point = f"POINT({lng} {lat})"

    chat_session = _get_own_session(booking_chat_id, db, current_user)

    raw_job_desc = payload.edited_description.strip()
    if not raw_job_desc:
        raw_job_desc = f"{payload.title}: {payload.contact_name or ''}".strip()

    if not chat_session.is_complete and not raw_job_desc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot process summary. The AI chat session is not complete yet. Please provide a job description.",
        )

    original_ai_desc = (chat_session.problem_description or "").strip()
    existing_categories = getattr(chat_session, "categories", [])

    if (
        not original_ai_desc
        or raw_job_desc != original_ai_desc
        or not existing_categories
    ):
        logger.info(
            f"[Booking {booking_chat_id}] Manual entry or modified description detected. Running AI refinement."
        )

        ai_data = await _refine_job_description_with_ai(raw_job_desc)
        final_job_desc = ai_data.get("refined_description", raw_job_desc)
        final_categories = ai_data.get("categories", [])

        if not final_categories and existing_categories:
            final_categories = existing_categories

    else:
        logger.info(
            f"[Booking {booking_chat_id}] Description matches original AI summary. Skipping refinement."
        )
        final_job_desc = raw_job_desc
        final_categories = existing_categories

    embedding_vector = await _fetch_nvidia_embedding(final_job_desc)
    address_text = await _get_address_from_coords(lat, lng)

    customer_fields = {
        "is_complete": getattr(chat_session, "is_complete", False),
        "is_job_request": getattr(chat_session, "is_job_request", False),
        "categories": final_categories,
        "problem_description": final_job_desc,
    }

    job_fields = {
        "title": payload.title,
        "description": final_job_desc,
        "status": payload.status,
        "is_job_request": getattr(chat_session, "is_job_request", True),
        "categories": final_categories,
        "contact_name": payload.contact_name,
        "contact_phone": payload.contact_phone,
        "mode": payload.mode,
        "scheduled_date": payload.scheduled_date,
        "attachments": payload.attachments,
        "latitude": lat,
        "longitude": lng,
        "location": wkt_point,
        "description_vector": embedding_vector,
        "address_text": address_text,
    }

    try:
        job_manager.upsert_chat_data(
            db, booking_chat_id, current_user.id, customer_fields
        )
        job_data = job_manager.upsert_job(
            db, booking_chat_id, current_user.id, job_fields
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Core entity persistence failed: {e}")
        raise HTTPException(status_code=500, detail="Database update failed.")

    try:
        matching_result = matching_manager.create_matches_for_job(
            db=db,
            job_id=job_data.id,
            query_vector=embedding_vector,
            customer_location=wkt_point,
            radius_meters=DEFAULT_SEARCH_RADIUS_METERS,
            job_description=final_job_desc,
        )
        db.commit()
    except Exception as engine_err:
        db.rollback()
        logger.error(
            f"Matching Engine execution forced transaction rollback: {engine_err}"
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to safely compile and record marketplace matches.",
        )

    job_payload = {
        "type": "NEW_JOB_NOTIFICATION",
        "data": {
            "booking_chat_id": booking_chat_id,
            "title": payload.title,
            "description": final_job_desc,
        }
    }

    if worker_chat_ids := matching_result.get("worker_chat_ids", []):
        background_tasks.add_task(
            _broadcast_notifications, worker_chat_ids, job_payload
        )

    return {
        "status": "success",
        "message": f"Job registered. Established {matching_result.get('count', 0)} matches successfully.",
    }


def _extract_primary_category(categories: list[dict]) -> tuple[str | None, bool]:
    if not categories:
        return None, False
    top = categories[0]
    return top.get("category"), bool(top.get("is_custom_category", False))


@router.get(
    "/match/{booking_chat_id}/find-help",
    response_model=schema.FindHelpOut,
    summary="Fetch pre-calculated matching workers for a completed job layout from DB",
)
def find_help(
    booking_chat_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):

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
        select(
            model.JobWorkerMatch,
            model.WorkerProfile,
            model.User.username,
            model.WorkerSkill,
        )
        .join(
            model.WorkerProfile,
            model.WorkerProfile.id == model.JobWorkerMatch.worker_id,
        )
        .join(model.User, model.User.id == model.WorkerProfile.user_id)
        .outerjoin(
            model.WorkerSkill,
            model.WorkerSkill.id == model.JobWorkerMatch.matched_skill_id,
        )
        .where(
            model.JobWorkerMatch.job_id == job_data.id,
            model.JobWorkerMatch.is_active == True,
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
            "matched_skill": skill.title if skill is not None else None,
            "matched_skill_description": (
                skill.description if skill is not None else None
            ),
            "is_interested": match.is_interested,
        }
        for match, worker, username, skill in matches
    ]

    return {
        "matched_by_category": bool(category),
        "category": category,
        "workers": workers,
    }


import io
import matplotlib.pyplot as plt
import seaborn as sns
from fastapi import Response


@match_router.get(
    "/match/{booking_chat_id}/validate-vectors",
    summary="Generate vector reliability validation charts",
)
def validate_vectors(
    booking_chat_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    job_data = db.execute(
        select(model.Job).where(
            model.Job.booking_chat_id == booking_chat_id,
            model.Job.customer_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not job_data or job_data.description_vector is None or job_data.location is None:
        raise HTTPException(
            status_code=400, detail="Invalid job data or missing vector."
        )

    distance = model.WorkerSkill.embedding.cosine_distance(job_data.description_vector)

    best_skill = (
        select(
            model.WorkerSkill.worker_id.label("worker_id"),
            distance.label("distance"),
        )
        .where(
            model.WorkerSkill.embedding.isnot(None),
            model.WorkerSkill.is_active.is_(True),
        )
        .distinct(model.WorkerSkill.worker_id)
        .order_by(model.WorkerSkill.worker_id, distance.asc())
        .subquery()
    )

    stmt = (
        select(model.WorkerProfile, best_skill.c.distance)
        .join(best_skill, best_skill.c.worker_id == model.WorkerProfile.id)
        .where(
            model.WorkerProfile.location.isnot(None),
            model.WorkerProfile.is_complete.is_(True),
            model.WorkerProfile.is_rejected.is_(False),
            func.ST_DWithin(
                model.WorkerProfile.location,
                job_data.location,
                DEFAULT_SEARCH_RADIUS_METERS,
            ),
        )
        .order_by(best_skill.c.distance.asc())
        .limit(50)
    )

    results = db.execute(stmt).all()
    if not results:
        raise HTTPException(
            status_code=404, detail="No regional workers found to validate against."
        )

    raw_distances = []
    calculated_scores = []

    for worker, dist in results:
        raw_distances.append(dist)
        score = max(
            0.0,
            min(
                100.0, round((1.0 / (1.0 + math.exp(25.0 * (dist - 0.90)))) * 100.0, 2)
            ),
        )
        calculated_scores.append(score)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    ax1.scatter(
        raw_distances,
        calculated_scores,
        color="purple",
        alpha=0.7,
        edgecolors="k",
        s=60,
        label="Worker Matches",
    )
    ax1.axvline(
        x=0.90, color="red", linestyle="--", label="Inflection Threshold (0.90)"
    )
    ax1.axhline(y=50.0, color="gray", linestyle=":")
    ax1.set_title("Sigmoid Scoring Curve Validation")
    ax1.set_xlabel("Raw Cosine Distance (Lower = Closer Meaning)")
    ax1.set_ylabel("Calculated Match Score (0 - 100)")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    sns.kdeplot(calculated_scores, fill=True, color="teal", ax=ax2, bw_adjust=0.5)
    ax2.set_title("Distribution Spectrum of Match Scores")
    ax2.set_xlabel("Match Score Output")
    ax2.set_ylabel("Density of Workers")
    ax2.set_xlim(-5, 105)

    plt.suptitle(
        f"Vector Reliability Analysis for Booking Chat ID: {booking_chat_id}",
        fontsize=14,
        y=0.98,
    )
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    return Response(content=buf.getvalue(), media_type="image/png")
