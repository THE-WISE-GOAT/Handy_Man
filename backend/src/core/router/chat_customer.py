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

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

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
    # booking_chat_id is already required+typed by the schema; this just
    # rejects nonsense values (<=0) that can never be a real primary key,
    # rather than the old `not payload.booking_chat_id` check, which would
    # have incorrectly rejected a (hypothetical) valid id of 0.
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
    # payload.message is already stripped and guaranteed non-empty by the
    # schema's field_validator — no whitespace-only messages reach history.
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
    # Force close if the model missed the signal but we've hit the hard cap
    force_complete = user_turn_count >= MAX_TURNS
    is_complete    = "[COMPLETE]" in ai_message or force_complete

    if force_complete and "[COMPLETE]" not in ai_message:
        # Append the tag so the extraction prompt gets the correct signal
        # in the persisted history (it filters system messages, not this tag)
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

            # Full per-trade breakdown — use this for actual worker routing,
            # since each entry's tags are scoped to the trade that owns them.
            categories_to_return = chat_session.categories

            # Flattened union of every tag across every trade — kept for
            # callers that just want "what tags should I match against"
            # without caring which trade each one belongs to.
            tags_to_return = sorted({
                tag for c in structured.categories for tag in c.tags
            })
            job_found = structured.is_job_request
            # True if ANY trade's match needed an invented category/tag —
            # signals at least one part of this job wants a manual glance.
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
            # Extraction itself failed (NIM down, malformed JSON, etc.) —
            # this is a pipeline error, not a legitimate "no job" outcome, so
            # don't let it look identical to one. Blank the fields the same
            # way a clean no-job result would, but log loudly so it gets
            # noticed and retried/investigated rather than silently treated
            # as "customer never asked for anything."
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
        "categories":          categories_to_return,
        "current_tags":        tags_to_return,
        "is_job_request":      job_found,
        "is_custom_category":  custom_category_flag,
        "turns_used":          turns_used,
        "turns_remaining":     turns_remaining,
    }


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