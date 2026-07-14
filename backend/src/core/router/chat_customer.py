"""
Dispatch router — AI-powered home-repair booking interview.

Endpoints
---------
  POST /dispatch/session
      Start a brand-new chat session.  Returns the opening greeting and
      the new booking_chat_id so the client can display it immediately
      before the customer has typed anything.

  POST /dispatch/chat
      Send one customer message and get the AI reply back.
      Automatically closes the session when [COMPLETE] is emitted or
      MAX_TURNS is reached and triggers the extraction pipeline.

  GET  /dispatch/{booking_chat_id}/history
      Fetch the full conversation so far (client-safe subset only —
      system prompt is stripped).

  GET  /dispatch/{booking_chat_id}/summary
      Fetch the structured extraction result once the session is complete.
      Returns 409 if called while the session is still in progress.
"""

import logging
from sqlalchemy import select, or_, func
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import requests, os
from src.database.database import get_db
from src.core.oauth2 import get_current_user
from src.core import model, schema
from src.ai.customer_chat_analyser_nvidia import (
    _nvidia_client,          # shared NIM client — no second API key needed
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
            # FIX: BookingChat has no `customer_id` column — the actual
            # foreign key on the model is `user_id`. This was raising an
            # AttributeError on every single call to this helper, i.e.
            # every endpoint below.
            model.BookingChat.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )
    return session


# ── 1. Start a new session ───────────────────────────────────────────────────

@router.post("/session",response_model=schema.SessionStartOut,status_code=status.HTTP_201_CREATED,summary="Create a new dispatch chat session",
)
def start_session(
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    """
    Creates a fresh BookingChat row, seeds the conversation history with
    the system prompt and the opening greeting, and returns the
    booking_chat_id + greeting to the client.

    Call this once when the customer opens the chat UI.
    """
    chat_session = model.BookingChat(
        # FIX: same customer_id -> user_id correction as _get_own_session
        # above, so newly created rows actually populate the real FK
        # column instead of failing immediately.
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


# ── 2. Send a message ────────────────────────────────────────────────────────

# @router.post(
#     "/chat",
#     response_model=schema.ChatMessageOut,
#     summary="Send a customer message and receive an AI reply",
# )
# def dispatch_chat(
#     payload: schema.ChatMessageIn,
#     db: Session = Depends(get_db),
#     current_user: model.User = Depends(get_current_user),
# ):
#     """
#     Handles one full conversation turn:
#     1. Validates the session and checks it is still open.
#     2. Appends the customer message to the persisted history.
#     3. Calls the NIM model with the full history so context is never lost.
#     4. Detects completion via [COMPLETE] or MAX_TURNS exhaustion.
#     5. On completion, runs the extraction pipeline and caches the
#        structured result — including whether a real job was found and,
#        per trade, whether it came from the static registry or the AI
#        fallback.
#     6. Commits everything in one transaction.
#     """
#     if payload.booking_chat_id <= 0:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="booking_chat_id must be a positive integer. Call POST /dispatch/session first.",
#         )
#     chat_session = _get_own_session(payload.booking_chat_id, db, current_user)
#     if chat_session.is_complete:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="This chat session is already completed. Start a new session.",
#         )
#     updated_history = list(chat_session.history)
#     updated_history.append({"role": "user", "content": payload.message})
#     user_turn_count = count_user_turns(updated_history)
#     try:
#         response = _nvidia_client.chat.completions.create(
#             model=MODEL_NAME,
#             messages=updated_history,
#             temperature=0.0,
#             max_tokens=512,
#         )
#     except Exception as exc:
#         raise HTTPException(
#             status_code=status.HTTP_502_BAD_GATEWAY,
#             detail=f"NVIDIA NIM inference error: {exc}",
#         )
#     ai_message: str = response.choices[0].message.content.strip()
#     force_complete = user_turn_count >= MAX_TURNS
#     is_complete    = "[COMPLETE]" in ai_message or force_complete
#     if force_complete and "[COMPLETE]" not in ai_message:
#         ai_message += " [COMPLETE]"
#     updated_history.append({"role": "assistant", "content": ai_message})
#     chat_session.history = updated_history
#     display_message = ai_message.replace("[COMPLETE]", "").strip()
#     categories_to_return:  list[dict] = []
#     tags_to_return:        list[str]  = []
#     job_found:              bool      = False
#     custom_category_flag:   bool      = False
#     if is_complete:
#         chat_session.is_complete = True
#         try:
#             structured = extract_final_json(chat_session.history, MODEL_NAME)
#             chat_session.categories          = [c.model_dump() for c in structured.categories]
#             chat_session.problem_description = structured.problem_description
#             chat_session.is_job_request       = structured.is_job_request
#             categories_to_return = chat_session.categories
#             tags_to_return = sorted({
#                 tag for c in structured.categories for tag in c.tags
#             })
#             job_found = structured.is_job_request
#             custom_category_flag = any(
#                 c.is_custom_category for c in structured.categories
#             )
#             if not structured.is_job_request:
#                 logger.info("[Dispatch] booking_chat_id=%s completed with no job extracted.", chat_session.id)
#         except Exception as extraction_err:
#             chat_session.categories          = []
#             chat_session.problem_description = ""
#             chat_session.is_job_request       = False
#             categories_to_return  = []
#             tags_to_return        = []
#             job_found              = False
#             custom_category_flag  = False
#             logger.error("[Dispatch] Extraction pipeline failure: %s", extraction_err)
#     try:
#         db.commit()
#     except Exception:
#         db.rollback()
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database write failure.")
#     turns_used      = user_turn_count
#     turns_remaining = max(0, MAX_TURNS - turns_used)
#     return {
#         "booking_chat_id":     chat_session.id,
#         "ai_response":         display_message,
#         "is_complete":         chat_session.is_complete,
#         "categories":          categories_to_return,
#         "current_tags":        tags_to_return,
#         "is_job_request":      job_found,
#         "is_custom_category":  custom_category_flag,
#         "turns_used":          turns_used,
#         "turns_remaining":     turns_remaining,
#         "problem_description": chat_session.problem_description,
#         "categories":          categories_to_return
#     }

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
    """
    Handles one full conversation turn:

    1. Validates the session and checks it is still open.
    2. Appends the customer message to the persisted history.
    3. Calls the NIM model with the full history so context is never lost.
    4. Detects completion via [COMPLETE] or MAX_TURNS exhaustion.
    5. On completion, runs the extraction pipeline and caches the
       structured result — including whether a real job was found and,
       per trade, whether it came from the static registry or the AI
       fallback.
    6. Commits everything in one transaction.
    """

    # ── Resolve session ───────────────────────────────────────────────────────
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

    # ── Append customer message ───────────────────────────────────────────────
    updated_history = list(chat_session.history)
    updated_history.append({"role": "user", "content": payload.message})
    user_turn_count = count_user_turns(updated_history)

    # ── Call the NIM model ───────────────────────────────────────────────────
    try:
        response = _nvidia_client.chat.completions.create(
            model=MODEL_NAME,
            messages=updated_history,
            temperature=0.0,
            max_tokens=512,   # system prompt enforces 1–2 sentence replies
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"NVIDIA NIM inference error: {exc}",
        )

    ai_message: str = response.choices[0].message.content.strip()

    # ── Completion detection ──────────────────────────────────────────────────
    force_complete = user_turn_count >= MAX_TURNS
    is_complete    = "[COMPLETE]" in ai_message or force_complete

    if force_complete and "[COMPLETE]" not in ai_message:
        ai_message += " [COMPLETE]"

    # Persist the raw AI message (with tag) before we strip it for display
    updated_history.append({"role": "assistant", "content": ai_message})
    chat_session.history = updated_history

    # ── Strip tag for client display ──────────────────────────────────────────
    display_message = ai_message.replace("[COMPLETE]", "").strip()

    # ── Extraction pipeline (only on completion) ──────────────────────────────
    categories_to_return:  list[dict] = []
    tags_to_return:        list[str]  = []
    job_found:              bool      = False
    custom_category_flag:   bool      = False

    if is_complete:
        chat_session.is_complete = True

        try:
            structured = extract_final_json(chat_session.history, MODEL_NAME)
            chat_session.categories          = [c.model_dump() for c in structured.categories]
            chat_session.problem_description = structured.problem_description
            chat_session.is_job_request       = structured.is_job_request

            categories_to_return = chat_session.categories

            tags_to_return = sorted({
                tag for c in structured.categories for tag in c.tags
            })
            job_found = structured.is_job_request
            custom_category_flag = any(
                c.is_custom_category for c in structured.categories
            )

            if not structured.is_job_request:
                logger.info(
                    "[Dispatch] booking_chat_id=%s completed with no dispatchable "
                    "job extracted (off-topic or empty conversation).",
                    chat_session.id,
                )
        except Exception as extraction_err:
            chat_session.categories          = []
            chat_session.problem_description = ""
            chat_session.is_job_request       = False

            categories_to_return  = []
            tags_to_return        = []
            job_found              = False
            custom_category_flag  = False

            logger.error(
                "[Dispatch] Extraction pipeline failure for booking_chat_id=%s: %s",
                chat_session.id, extraction_err,
            )

    # ── Persist ───────────────────────────────────────────────────────────────
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database write failure.",
        )

    turns_used      = user_turn_count
    turns_remaining = max(0, MAX_TURNS - turns_used)

    return {
        "booking_chat_id":     chat_session.id,
        "ai_response":         display_message,
        "is_complete":         chat_session.is_complete,
        "current_tags":        tags_to_return,
        "is_job_request":      job_found,
        "is_custom_category":  custom_category_flag,
        "turns_used":          turns_used,
        "turns_remaining":     turns_remaining,
        "problem_description": chat_session.problem_description,
        "categories":          categories_to_return
    }


# use to post  the  customer  retrieve from chat to  database and also handle the  vector embedding from nvidia and save to database
# ── Consolidated complete_customer_chat endpoint ──
@router.post(
    "/{booking_chat_id}/complete",
    summary="Complete the AI chat, extract job explained keys, generate embedding, and save to DB",
)
def complete_customer_chat(
    booking_chat_id: int, 
    payload: schema.CompleteChatIn, # Accepts the edited text block parameters from the UI layout payload
    db: Session = Depends(get_db), 
    current_user: model.User = Depends(get_current_user)
):
    
    lng = payload.location.longitude
    lat = payload.location.latitude

    wkt_point = f"POINT({lng} {lat})"

    # Step 1 / 1. Verify and fetch the chat session
    chat_session = _get_own_session(booking_chat_id, db, current_user)

    if not chat_session.is_complete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot process summary. The AI chat session is not complete yet.",
        )
    
    # Step 2 / 2. Extract incoming values from frontend payload
    # CRITICAL REFINEMENT: Pull the customized, finalized description value directly from the user's edits
    job_desc = payload.edited_description.strip()
    
    # Optional: Raise error if a job description was mandatory for your app logic
    if not job_desc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description is missing. Cannot generate vector profile."
        )

    # Step 3 / 3. Request Vector Embedding from Nvidia
    embedding_vector = None
    try:
        headers = {
            "Authorization": f"Bearer {os.getenv('NVIDIA_API_KEY')}",
            "Content-Type": "application/json"
        }
        # The Nvidia payload now matches exactly what the customer finalized on screen
        nvidia_payload = {
            "model": "nvidia/nv-embed-v1",
            "input": [job_desc],
            "input_type": "query",
            "encoding_format": "float"
        }

        response = requests.post(
           "https://integrate.api.nvidia.com/v1/embeddings",
           headers=headers, 
           json=nvidia_payload, 
           timeout=10.0
        )
        
        if response.status_code == 200:
            embedding_vector = response.json()["data"][0]["embedding"]
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Nvidia API error: {response.status_code} - {response.text}"
            )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to Nvidia API: {e}"
        )
        
    # Step 2 / 4. Check for existing data profile to prevent duplicate rows / primary key crashes
    db_profile = db.query(model.CustomerChatData).filter(
        model.CustomerChatData.booking_chat_id == booking_chat_id,
        model.CustomerChatData.user_id == current_user.id
    ).first()

    # ... keep your vector code ...
    customer_fields = {
        "is_complete": getattr(chat_session, "is_complete", False),
        "is_job_request": getattr(chat_session, "is_job_request", False),
        "categories": getattr(chat_session, "categories", []), 
        "problem_description": job_desc,
        "location": wkt_point,
        "description_vector": embedding_vector 
    }

    if db_profile:
        # If record exists, update its values (Upsert)
        for key, value in customer_fields.items():
            setattr(db_profile, key, value)
    else:
        # If record does not exist, create a new one
        db_profile = model.CustomerChatData(
            user_id=current_user.id,
            booking_chat_id=booking_chat_id,
            **customer_fields
        )
    db.add(db_profile)
        
    db.commit()
    return {"status": "success", "message": "Customer chat data structured and saved successfully."}


# ── 3. Retrieve conversation history ─────────────────────────────────────────

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
    """
    Returns the client-visible conversation (system prompt is stripped).
    Useful for restoring the chat UI after a page reload.
    """
    chat_session = _get_own_session(booking_chat_id, db, current_user)

    # Strip the raw [COMPLETE] tag from the assistant's own completion
    # message only — never touch customer-typed content. A customer who
    # happens to type the literal string "[COMPLETE]" should see exactly
    # what they typed when the history is reloaded.
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

    #endpoint here
    
    return {
        "booking_chat_id":  chat_session.id,
        "history":          visible_history,
        "is_complete":      chat_session.is_complete,
        "turns_used":       count_user_turns(chat_session.history),
        "turns_remaining":  max(0, MAX_TURNS - count_user_turns(chat_session.history)),
    }


# ── 4. Structured summary ─────────────────────────────────────────────────────

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
    """
    Returns the validated extraction payload.

    is_job_request=False means no real job was ever extracted from this
    session (off-topic conversation, or the extraction pipeline failed) —
    callers should NOT dispatch a worker for it.

    categories is a list of per-trade matches, most central trade first.
    Each entry's is_custom_category=True means that trade's category/tags
    came from the AI fallback rather than an exact SERVICE_REGISTRY match —
    route that entry to a manual-matching / review flow instead of
    automated worker-tag matching; entries with is_custom_category=False
    can be auto-routed as-is.

    Returns 409 Conflict if the session is not yet complete — don't
    poll this; check the is_complete flag in the chat response instead.
    """
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


# ── Helper: pick the primary category ────────────────────────────────────────

def _select_primary_category(categories: list[dict]) -> tuple[str | None, bool]:
    """
    Pick the primary (most central) trade from the customer's extracted
    categories and report whether it came from the static registry or
    the AI fallback.

    categories is ordered most-central-trade-first (see BookingSummaryOut
    docstring), so the first entry is authoritative for filtering.

    Returns (category_name, is_custom). category_name is None if the
    customer has no extracted categories at all.
    """
    if not categories:
        return None, False
    top = categories[0]
    return top.get("category"), bool(top.get("is_custom_category", False))


# ── Helper: cosine-similarity worker search ──────────────────────────────────

def _vector_search_workers(
    db: Session,
    query_vector: list[float],
    category: str | None,
    limit: int = 5,
):
    """
    Rank WorkerProfile rows by cosine distance against `query_vector`.

    If `category` is given, restricts the candidate pool to workers whose
    job_category OR category_tag matches it (case-insensitive) before
    ranking — the "category found" fast path. If `category` is None,
    ranks across every eligible worker — the semantic-only fallback.

    Only considers workers who finished vetting, weren't rejected, and
    actually have an embedding to compare against.

    Returns a list of (WorkerProfile, username, cosine_distance) rows,
    closest first.
    """
    distance = model.WorkerProfile.description_vector.cosine_distance(query_vector)

    stmt = (
        select(model.WorkerProfile, model.User.username, distance.label("distance"))
        .join(model.User, model.User.id == model.WorkerProfile.user_id)
        .where(
            model.WorkerProfile.description_vector.isnot(None),
            model.WorkerProfile.is_complete.is_(True),
            model.WorkerProfile.is_rejected.is_(False),
        )
    )

    if category:
        stmt = stmt.where(
            or_(
                func.lower(model.WorkerProfile.job_category) == category.lower(),
                func.lower(model.WorkerProfile.category_tag) == category.lower(),
            )
        )

    stmt = stmt.order_by(distance).limit(limit)
    return db.execute(stmt).all()


# ── 5. Find help — match customer job to top workers ─────────────────────────

@router.get(
    "/match/{booking_chat_id}/find-help",
    response_model=schema.FindHelpOut,
    summary="Find the top 5 matching workers for a completed job request",
)
@match_router.get(
    "/match/{booking_chat_id}/find-help",
    response_model=schema.FindHelpOut,
    summary="Find the top 5 matching workers for a completed job request",
)
def find_help(
    booking_chat_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    """
    Powers the customer's "Find Help" button.

    Requires that POST /dispatch/{booking_chat_id}/complete has already
    run for this session (that's what populates description_vector).

    Strategy: category-aware match first (see _select_primary_category /
    _vector_search_workers docstrings), falling back to a pure semantic
    match over all workers if there's no usable category or the
    category-filtered pool is empty.
    """
    customer_data = db.execute(
        select(model.CustomerChatData).where(
            model.CustomerChatData.booking_chat_id == booking_chat_id,
            model.CustomerChatData.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not customer_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No embedded job data found for this booking_chat_id. "
                   "Call POST /dispatch/{booking_chat_id}/complete first.",
        )

    if customer_data.description_vector is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This job has no embedding yet — cannot search for workers.",
        )

    if not customer_data.is_job_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This chat session was not a dispatchable job request.",
        )

    category, is_custom = _select_primary_category(customer_data.categories or [])
    used_category_filter = bool(category) and not is_custom

    matches = []
    if used_category_filter:
        matches = _vector_search_workers(
            db, customer_data.description_vector, category=category, limit=5,
        )

    if not matches:
        # No usable category, a custom/invented one, or the filtered pool
        # was empty — fall back to pure semantic search over everyone.
        used_category_filter = False
        matches = _vector_search_workers(
            db, customer_data.description_vector, category=None, limit=5,
        )

    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching workers found.",
        )

    workers = [
        {
            "worker_chat_id": worker.worker_chat_id,
            "username": username,
            "job_category": worker.job_category,
            "category_tag": worker.category_tag,
            "job_description": worker.job_description,
            # "match_score": round(1 - distance, 4),
        }
        for worker, username, distance in matches
    ]

    return {
        "matched_by_category": used_category_filter,
        "category": category,
        "workers": workers,
    }