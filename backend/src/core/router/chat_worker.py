"""
Worker interview router — AI-powered worker registration & vetting.

Endpoints
---------
  POST /worker-interview/session
      Start a brand-new interview session. Returns the opening greeting
      and the new worker_chat_id so the client can display it immediately.

  POST /worker-interview/chat
      Send one worker message and get the AI's next step back. Internally
      drives a small state machine:
        interviewing             -> ordinary Q&A turn
        awaiting_scenario_answer -> the message is graded as the answer to
                                     the last scenario question, not
                                     treated as a normal chat turn
        complete                 -> session is closed; use /summary

  GET  /worker-interview/{worker_chat_id}/history
      Fetch the full conversation so far (system prompt stripped).

  GET  /worker-interview/{worker_chat_id}/summary
      Fetch the structured profile once the session is complete. Returns
      409 if called while still in progress.

Server-side invariants (do not weaken these without re-reading
worker_interview_nvidia.py's module docstring first):
  - A session can only become is_complete=True through
    _handle_scenario_answer, i.e. only after evaluate_answer() has
    actually graded a real answer. A bare [COMPLETE] token emitted during
    the "interviewing" stage is stripped and ignored, never honored.
  - MAX_PRETEST_TURNS is enforced here, not just via the system prompt's
    RULE 6 — see the forced-resolution block in _handle_interview_turn.
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.database.database import get_db
from src.core.oauth2 import get_current_user
from src.core import model, schema
import requests
from src.ai.worker_chat_analyser_nvidia import (
    _nvidia_client,          # shared NIM client — same instance dispatch.py uses
    build_fresh_history,
    count_user_turns,
    generate_scenario,
    evaluate_answer,
    extract_worker_profile,
    INITIAL_GREETING,
    MAX_PRETEST_TURNS,
    MODEL_NAME,
    REJECTION_TOKEN,
    TEST_TOKEN_RE,
    COMPLETE_TOKEN,
    SCENARIO_PASS_THRESHOLD,
)

router = APIRouter(prefix="/worker-interview", tags=["Worker Interview"])
logger = logging.getLogger(__name__)


# ── Helper ───────────────────────────────────────────────────────────────────

def _get_own_worker_session(
    worker_chat_id: int,
    db: Session,
    current_user: model.User,
) -> model.WorkerInterviewSession:
    """Fetch a WorkerInterviewSession that belongs to the current user; 404 if missing."""
    chat_session = db.execute(
        select(model.WorkerInterviewSession).where(
            model.WorkerInterviewSession.id == worker_chat_id,
            model.WorkerInterviewSession.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not chat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker interview session not found.",
        )
    return chat_session


# ── 1. Start a new session ───────────────────────────────────────────────────

@router.post(
    "/session",
    response_model=schema.WorkerSessionStartOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new worker interview session",
)
def start_worker_session(
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    chat_session = model.WorkerInterviewSession(
        user_id=current_user.id,
        history=build_fresh_history(),
        stage="interviewing",
        is_complete=False,
        is_rejected=False,
    )
    db.add(chat_session)

    try:
        db.commit()
        db.refresh(chat_session)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create worker interview session.",
        )

    return {
        "worker_chat_id": chat_session.id,
        "ai_response": INITIAL_GREETING,
        "stage": chat_session.stage,
    }


# ── 2. Send a message ────────────────────────────────────────────────────────

@router.post(
    "/chat",
    response_model=schema.WorkerChatMessageOut,
    summary="Send a worker message and receive the next interview step",
)
def worker_chat(
    payload: schema.WorkerChatMessageIn,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    if payload.worker_chat_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="worker_chat_id must be a positive integer. Call POST /worker-interview/session first.",
        )

    chat_session = _get_own_worker_session(payload.worker_chat_id, db, current_user)

    if chat_session.is_complete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This interview is already complete. Start a new session to re-apply.",
        )

    message = payload.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message cannot be empty.",
        )

    if chat_session.stage == "awaiting_scenario_answer":
        return _handle_scenario_answer(chat_session, message, db)

    return _handle_interview_turn(chat_session, message, db)


def _handle_scenario_answer(
    chat_session: model.WorkerInterviewSession,
    answer: str,
    db: Session,
) -> dict:
    """
    The worker's message here is their answer to the last scenario
    question, not an ordinary chat turn. This is the ONLY place a session
    is allowed to become is_complete=True — see the module docstring.
    """
    history = list(chat_session.history)
    history.append({"role": "user", "content": answer})

    try:
        passed, score, report = evaluate_answer(
            sub_skill=chat_session.pending_sub_skill,
            scenario=chat_session.pending_scenario,
            answer=answer,
            model_name=MODEL_NAME,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"NVIDIA NIM evaluation error: {exc}",
        )

    chat_session.scenario_score = score
    chat_session.scenario_passed = passed

    if passed:
        # Record the system-verified result in history — never the raw
        # model's self-report — so the extraction step and the audit
        # trail both see exactly what happened here.
        history.append({
            "role": "assistant",
            "content": (
                f"[TEST_REQUIRED: {chat_session.pending_sub_skill}]\n"
                f"System record: worker answered the scenario test. "
                f"Evaluator score: {score}/100. Result: PASS. {COMPLETE_TOKEN}"
            ),
        })
        chat_session.history = history

        try:
            profile = extract_worker_profile(
                history=history,
                pending_sub_skill=chat_session.pending_sub_skill,
                has_verified_specialty=bool(chat_session.has_verified_specialty),
                scenario_score=score,
                model_name=MODEL_NAME,
            )
            chat_session.profile = profile.model_dump()
            ai_response = "Technical verification complete. Your profile has been registered."
        except Exception as extraction_err:
            # A passed test with a failed extraction is a pipeline error,
            # not a rejection — don't discard a legitimate pass. Leave the
            # session complete-but-unprofiled and log loudly so it gets
            # retried/reviewed rather than silently treated as a fail.
            chat_session.profile = None
            ai_response = (
                "Technical verification complete, but we hit an internal "
                "error building your profile. Our team will finish this "
                "manually — no need to redo the interview."
            )
            logger.error(
                "[WorkerInterview] Extraction failure for worker_chat_id=%s: %s",
                chat_session.id, extraction_err,
            )

        chat_session.stage = "complete"
        chat_session.is_complete = True
        chat_session.is_rejected = False

    else:
        history.append({
            "role": "assistant",
            "content": (
                f"[TEST_REQUIRED: {chat_session.pending_sub_skill}]\n"
                f"System record: worker answered the scenario test. "
                f"Evaluator score: {score}/100. Result: FAIL. {REJECTION_TOKEN}"
            ),
        })
        chat_session.history = history
        chat_session.stage = "complete"
        chat_session.is_complete = True
        chat_session.is_rejected = True
        chat_session.rejection_reason = (
            f"Scenario test failed — score {score}/100 (required above "
            f"{SCENARIO_PASS_THRESHOLD}) for '{chat_session.pending_sub_skill}'."
        )
        ai_response = (
            "Your answer did not demonstrate enough field knowledge for "
            "this role. This application cannot proceed right now."
        )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database write failure.",
        )

    turns_used = count_user_turns(chat_session.history)
    return {
        "worker_chat_id": chat_session.id,
        "ai_response": ai_response,
        "stage": chat_session.stage,
        "is_complete": chat_session.is_complete,
        "is_rejected": chat_session.is_rejected,
        "scenario_question": None,
        "turns_used": turns_used,
        "turns_remaining": max(0, MAX_PRETEST_TURNS - turns_used),
    }


def _handle_interview_turn(
    chat_session: model.WorkerInterviewSession,
    message: str,
    db: Session,
) -> dict:
    history = list(chat_session.history)
    history.append({"role": "user", "content": message})
    turns_used = count_user_turns(history)

    try:
        response = _nvidia_client.chat.completions.create(
            model=MODEL_NAME,
            messages=history,
            temperature=0.0,
            max_tokens=200,   # system prompt enforces short replies
        )
        ai_reply: str = response.choices[0].message.content.strip()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"NVIDIA NIM inference error: {exc}",
        )

    # ── Server-side hard cap ───────────────────────────────────────────────
    # RULE 6 in the system prompt asks the model to self-resolve by
    # question 8, but that's a prompt instruction, not a guarantee. If
    # we're out of runway and it still hasn't emitted REJECTED or
    # TEST_REQUIRED, force one more directed call before failing closed.
    if (
        turns_used >= MAX_PRETEST_TURNS
        and REJECTION_TOKEN not in ai_reply
        and not TEST_TOKEN_RE.search(ai_reply)
    ):
        history.append({"role": "assistant", "content": ai_reply})
        history.append({
            "role": "system",
            "content": (
                "The interview has run long. Based on everything discussed "
                "so far, respond with ONLY one of: "
                f"{REJECTION_TOKEN}, or [TEST_REQUIRED: <speciality, or "
                "'<job> — general competency' if none was found>]. "
                "No other text."
            ),
        })
        try:
            forced = _nvidia_client.chat.completions.create(
                model=MODEL_NAME,
                messages=history,
                temperature=0.0,
                max_tokens=60,
            )
            ai_reply = forced.choices[0].message.content.strip()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"NVIDIA NIM inference error: {exc}",
            )

        if REJECTION_TOKEN not in ai_reply and not TEST_TOKEN_RE.search(ai_reply):
            # Still didn't resolve — fail closed rather than loop forever.
            ai_reply = REJECTION_TOKEN

    # ── Rejection ────────────────────────────────────────────────────────
    if REJECTION_TOKEN in ai_reply:
        history.append({"role": "assistant", "content": ai_reply})
        chat_session.history = history
        chat_session.stage = "complete"
        chat_session.is_complete = True
        chat_session.is_rejected = True
        chat_session.rejection_reason = "Did not meet minimum interview requirements."

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database write failure.",
            )

        return {
            "worker_chat_id": chat_session.id,
            "ai_response": (
                "Thank you for your time. Your application does not meet "
                "our minimum requirements at this stage."
            ),
            "stage": chat_session.stage,
            "is_complete": True,
            "is_rejected": True,
            "scenario_question": None,
            "turns_used": turns_used,
            "turns_remaining": 0,
        }

    # ── Scenario test triggered ─────────────────────────────────────────
    test_match = TEST_TOKEN_RE.search(ai_reply)
    if test_match:
        sub_skill = test_match.group(1).strip()
        has_verified_specialty = "general competency" not in sub_skill.lower()

        visible_reply = ai_reply[: test_match.start()].strip()
        history.append({"role": "assistant", "content": ai_reply})

        try:
            scenario = generate_scenario(sub_skill, MODEL_NAME)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"NVIDIA NIM scenario generation error: {exc}",
            )

        chat_session.history = history
        chat_session.stage = "awaiting_scenario_answer"
        chat_session.pending_sub_skill = sub_skill
        chat_session.pending_scenario = scenario
        chat_session.has_verified_specialty = has_verified_specialty

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database write failure.",
            )

        ai_response = (visible_reply + "\n\n" + scenario).strip() if visible_reply else scenario

        return {
            "worker_chat_id": chat_session.id,
            "ai_response": ai_response,
            "stage": chat_session.stage,
            "is_complete": False,
            "is_rejected": False,
            "scenario_question": scenario,
            "turns_used": turns_used,
            "turns_remaining": max(0, MAX_PRETEST_TURNS - turns_used),
        }

    # ── Normal question turn ────────────────────────────────────────────
    # A bare COMPLETE_TOKEN here is never honored — completion can only
    # happen through _handle_scenario_answer after a real graded test. If
    # the model emits one anyway, it's stripped and treated as plain text.
    display = ai_reply.replace(COMPLETE_TOKEN, "").strip()
    history.append({"role": "assistant", "content": display})
    chat_session.history = history

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database write failure.",
        )

    return {
        "worker_chat_id": chat_session.id,
        "ai_response": display,
        "stage": "interviewing",
        "is_complete": False,
        "is_rejected": False,
        "scenario_question": None,
        "turns_used": turns_used,
        "turns_remaining": max(0, MAX_PRETEST_TURNS - turns_used),
    }


# ── 3. Retrieve conversation history ─────────────────────────────────────────

@router.get(
    "/{worker_chat_id}/history",
    response_model=schema.WorkerChatHistoryOut,
    summary="Get the full conversation history for a session",
)
def get_worker_history(
    worker_chat_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    chat_session = _get_own_worker_session(worker_chat_id, db, current_user)

    # Strip the raw control tokens from the assistant's own messages only
    # — never touch worker-typed content, even if they happen to type a
    # literal "[COMPLETE]" or "[REJECTED]".
    visible_history = [
        {
            "role": msg["role"],
            "content": (
                msg["content"].replace(COMPLETE_TOKEN, "").strip()
                if msg["role"] == "assistant"
                else msg["content"]
            ),
        }
        for msg in chat_session.history
        if msg["role"] != "system"
    ]

    turns_used = count_user_turns(chat_session.history)
    return {
        "worker_chat_id": chat_session.id,
        "history": visible_history,
        "stage": chat_session.stage,
        "is_complete": chat_session.is_complete,
        "turns_used": turns_used,
        "turns_remaining": max(0, MAX_PRETEST_TURNS - turns_used),
    }


# ── 4. Structured summary ─────────────────────────────────────────────────────
@router.get(
    "/{worker_chat_id}/summary",
    response_model=schema.WorkerSummaryOut,
    summary="Get the structured worker profile (only available after completion)",
)
def get_worker_summary(
    worker_chat_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    """
    is_rejected=True means no profile was produced — check
    rejection_reason for why. profile is populated only on a genuine pass;
    it can still be None even when is_rejected=False if extraction itself
    failed after a passed test (see _handle_scenario_answer) — treat that
    combination as "needs manual follow-up," not as a rejection.

    Returns 409 Conflict if the session is not yet complete.
    """
    chat_session = _get_own_worker_session(worker_chat_id, db, current_user)

    if not chat_session.is_complete:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Interview is not yet complete. No summary is available.",
        )

    return {
        "stage": chat_session.stage,
        "is_complete": chat_session.is_complete,
        "is_rejected": chat_session.is_rejected,
        "rejection_reason": chat_session.rejection_reason,
        "profile": chat_session.profile,
    }




@router.post(
    "/{worker_chat_id}/complete",
    summary="Complete the AI chat, extract profile keys, generate embedding, and save to DB",
)
def complete_worker_chat(
    worker_chat_id: int, 
    payload: schema.WorkerCompleteChatIn,  # Expects location (latitude, longitude)
    db: Session = Depends(get_db), 
    current_user: model.User = Depends(get_current_user)
):
    # Step 1: Get the completed AI chat session
    chat_session = _get_own_worker_session(worker_chat_id, db, current_user)

    if not chat_session.is_complete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot process summary. The AI chat session is not complete yet.",
        )
        
    profile_data = chat_session.profile if chat_session.profile else {}
    job_desc = profile_data.get("job_description", "")
    
    lng = payload.location.longitude
    lat = payload.location.latitude
    wkt_point = f"POINT({lng} {lat})"
    
    # Step 3: Get Vector Embedding from Nvidia
    embedding_vector = None
    if job_desc:
        try:
            headers = {
            "Authorization": f"Bearer {os.getenv('NVIDIA_API_KEY')}",
            "Content-Type": "application/json"
            }
            payload = {
                "model": "nvidia/nv-embed-v1",
                "input": [job_desc],
                "input_type": "passage",
                "encoding_format": "float"
            }
    
            response = requests.post(
               "https://integrate.api.nvidia.com/v1/embeddings",
               headers=headers, 
               json=payload, 
               timeout=20.0
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
    else:
        # Optional: Raise error if a job description was mandatory for your app logic
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description is missing. Cannot generate vector profile."
        )
        
    # Step 2: Check if WorkerProfile already exists (to prevent duplicate primary key crashes)
    db_profile = db.query(model.WorkerProfile).filter(
        model.WorkerProfile.worker_chat_id == worker_chat_id,
        model.WorkerProfile.user_id == current_user.id
    ).first()

    # Define the dictionary of key-value data extracted from JSON summary
    profile_fields = {
        "stage": chat_session.stage,
        "is_complete": chat_session.is_complete,
        "is_rejected": chat_session.is_rejected,
        "rejection_reason": chat_session.rejection_reason,
        "job_category": profile_data.get("job_category"),
        "category_tag": profile_data.get("category_tag"),
        "is_custom_category": profile_data.get("is_custom_category", False),
        "specialities": profile_data.get("specialities", []),
        "years_experience": profile_data.get("years_experience", 0),
        "license_or_certification": profile_data.get("license_or_certification"),
        "specialized_tools_or_equipment": profile_data.get("specialized_tools_or_equipment", []),
        "job_description": job_desc,
        "emergency_available": profile_data.get("emergency_available", False),
        "has_verified_specialty": profile_data.get("has_verified_specialty", False),
        "scenario_passed": profile_data.get("scenario_passed", False),
        "scenario_score": profile_data.get("scenario_score", 0),
        "description_vector": embedding_vector,
        "latitude": lat,
        "longitude": lng,
        "location": wkt_point,
    }

    if db_profile:
        # If record exists, update its values (Upsert)
        for key, value in profile_fields.items():
            setattr(db_profile, key, value)
    else:
        # If record does not exist, create a new one
        db_profile = model.WorkerProfile(
            user_id=current_user.id,
            worker_chat_id=worker_chat_id,
            **profile_fields
        )
    db.add(db_profile)
        
    db.commit()
    
    return {"status": "success", "message": "Worker profile structured and saved successfully."}

    
    
    
    
    