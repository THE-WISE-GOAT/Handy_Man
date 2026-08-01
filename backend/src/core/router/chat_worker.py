"""
Worker interview router — AI-powered worker registration & vetting.

Endpoints
---------
  POST /worker-interview/session
  POST /worker-interview/chat
  GET  /worker-interview/{worker_chat_id}/history
  GET  /worker-interview/{worker_chat_id}/summary
  POST /worker-interview/{worker_chat_id}/complete
  GET  /worker-interview/{worker_chat_id}/skills
  POST /worker-interview/{worker_chat_id}/add-skill
  POST /worker-interview/{worker_chat_id}/add-skill/chat

SKILLS ARE ADDITIVE, PER TRADE
------------------------------
One 'baseline' row + zero-or-more 'speciality' rows per trade.
Matching scores on BEST-fitting row, not a blended vector.

  Same trade, another skill -> /add-skill (new row, vectors untouched)
  Different trade            -> POST /session (fresh interview, separate worker row)
"""

import logging
import re
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.core.oauth2 import get_current_user
from src.core import model, schema, matching_manager
from src.core.manager import manager
from src.ai.worker_chat_analyser_nvidia import (
    _nvidia_client,
    build_fresh_history,
    count_user_turns,
    generate_scenario,
    generate_speciality_description,
    evaluate_answer,
    extract_worker_profile,
    get_worker_description_embedding,
    is_general_competency_test,
    ADD_SKILL_GREETING,
    INITIAL_GREETING,
    MAX_PRETEST_TURNS,
    MODEL_NAME,
    REJECTION_TOKEN,
    TEST_TOKEN_RE,
    COMPLETE_TOKEN,
    SCENARIO_PASS_THRESHOLD,
)
from src.core.worker_profile_helper import (
    sync_profile_extracted_fields,
    upsert_baseline_skill,
    upsert_speciality_skill,
    active_skill_titles,
)

router = APIRouter(prefix="/worker-interview", tags=["Worker Interview"])
logger = logging.getLogger(__name__)

DEFAULT_SEARCH_RADIUS_METERS = 60_000  # 60 km hard marketplace cutoff

# ── Local control-signal regex (router-owned, not imported) ──────────────────
# Matches [TEST_REQUIRED: some text] case-insensitively, handles extra spaces.
_ADD_SKILL_TEST_RE = re.compile(r"\[TEST_REQUIRED\s*:\s*(.+?)\]", re.IGNORECASE)
_ADD_SKILL_REJECTED_RE = re.compile(r"\[REJECTED\]", re.IGNORECASE)


# ═══════════════════════════════════════════════════════════════════════════════
# ADD-SKILL PROMPT  (self-contained here so the router fully controls it)
# ═══════════════════════════════════════════════════════════════════════════════

_ADD_SKILL_SYSTEM_PROMPT = """\
You are a specialist skill assessor for a trades marketplace platform.
Your only job: decide whether a {job_category} worker is claiming a GENUINE,
SPECIFIC NEW SPECIALITY that is not already covered by their existing verified skills.

EXISTING VERIFIED SKILLS: {existing_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DECISION FRAMEWORK — follow in order, stop at first match
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 1 — DUPLICATE CHECK
  If the claimed skill is substantially the same as one already in
  EXISTING VERIFIED SKILLS (same equipment, same technique, same niche):
  → Emit exactly: [REJECTED]
  → Reason: "Already on profile."

STEP 2 — SPECIFICITY CHECK  (most messages pass here immediately)
  A claim is SPECIFIC ENOUGH to test if it contains ANY of:
    • Named sub-trade niche          e.g. "inverter/UPS calibration",
                                          "solar PV commissioning",
                                          "three-phase motor rewinding",
                                          "surge protection installation",
                                          "earthing system design",
                                          "data-centre UPS servicing",
                                          "EV charger installation",
                                          "fibre-optic splicing",
                                          "building management systems (BMS)",
                                          "high-voltage switchgear",
                                          "emergency lighting systems"
    • Named equipment or brand       e.g. "Pure Sine Wave inverters",
                                          "Schneider ATS panels",
                                          "Victron MPPT controllers"
    • Named standard or regulation   e.g. "IEC 60364", "BS 7671", "NEC 690"
    • Named environment or context   e.g. "monsoon lightning protection",
                                          "offshore installations",
                                          "food-grade cold-room wiring"
    • Any compound noun that is more specific than the base trade
      (e.g. "surge protection devices (SPDs)" is more specific than "electrical work")
  → Immediately emit: [TEST_REQUIRED: <the specific niche as the worker named it>]
  → Do NOT ask any follow-up. Do NOT say "most workers do that."
  → The scenario test will determine whether the claim is genuine.

STEP 3 — SINGLE CLARIFYING QUESTION  (only if Step 2 did not trigger)
  If the message is genuinely vague (e.g. "some electrical jobs", "maintenance work")
  and contains none of the Step 2 signals:
  → Ask ONE short, precise question:
    "Can you name the specific equipment, technique, or niche you specialise in?"
  → Do not explain. Do not apologise. Do not list examples.
  → After ONE clarifying answer: go back to Step 2. If still vague → [REJECTED].

STEP 4 — OUT-OF-TRADE CHECK
  If the claimed skill is clearly outside {job_category} entirely
  (e.g. a plumber claiming brain surgery):
  → Emit: [REJECTED]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ABSOLUTE PROHIBITIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✗ NEVER say "most {job_category}s do that" — you are NOT the arbiter of
  what is rare in the trade. The scenario test handles that.
✗ NEVER ask more than ONE clarifying question across the whole conversation.
✗ NEVER require the worker to prove rarity before testing.
✗ NEVER add your own commentary around a control token.
  Output ONLY the token when emitting [TEST_REQUIRED: ...] or [REJECTED].

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Trigger scenario test  →  [TEST_REQUIRED: <exact niche title>]
  Ask one follow-up      →  Plain question text only (no token, ≤ 20 words)
  Decline                →  [REJECTED]

Maximum response length: 25 words. No preamble. No explanation.\
"""


def _build_add_skill_messages(
    job_category: str,
    existing_skills: list[str],
    turns: list[dict],
) -> list[dict]:
    """
    Build the full message list for one add-skill turn.

    The system prompt is entirely self-contained here so the router is
    never at the mercy of whatever wording lives in worker_chat_analyser_nvidia.
    """
    existing_str = ", ".join(existing_skills) if existing_skills else "none yet"
    system_content = _ADD_SKILL_SYSTEM_PROMPT.format(
        job_category=job_category or "trades",
        existing_str=existing_str,
    )
    return [{"role": "system", "content": system_content}] + list(turns)


def _parse_add_skill_signal(reply: str) -> tuple[str, str | None]:
    """
    Robustly extract the control signal from the LLM reply.

    Returns
    -------
    ("test",     sub_skill_str)   – scenario test should be issued
    ("rejected", None)            – skill declined (worker profile unchanged)
    ("message",  None)            – ordinary follow-up question
    """
    test_match = _ADD_SKILL_TEST_RE.search(reply)
    if test_match:
        return "test", test_match.group(1).strip()

    if _ADD_SKILL_REJECTED_RE.search(reply):
        return "rejected", None

    # ── Fallback heuristics: the model sometimes paraphrases instead of
    #    emitting the exact token. Catch the most common cases so a valid
    #    speciality claim is never silently swallowed. ──────────────────
    lower = reply.lower()

    # "I'll test you on X" / "Let me test your knowledge of X"
    test_phrase = re.search(
        r"(?:i(?:'ll| will)|let(?:'s| us)|time to|ready to)\s+test\s+(?:you\s+)?(?:on\s+)?(.+)",
        lower,
    )
    if test_phrase:
        candidate = test_phrase.group(1).strip().rstrip(".!?")
        if candidate:
            return "test", candidate

    # "proceed to verify X" / "moving on to verify X"
    verify_phrase = re.search(
        r"(?:proceed|moving on|going)\s+to\s+verify\s+(.+)",
        lower,
    )
    if verify_phrase:
        candidate = verify_phrase.group(1).strip().rstrip(".!?")
        if candidate:
            return "test", candidate

    return "message", None


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _get_own_worker_session(
    worker_chat_id: int,
    db: Session,
    current_user: model.User,
) -> model.WorkerInterviewSession:
    """Fetch a WorkerInterviewSession owned by current_user; raise 404 otherwise."""
    session = db.execute(
        select(model.WorkerInterviewSession).where(
            model.WorkerInterviewSession.id == worker_chat_id,
            model.WorkerInterviewSession.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker interview session not found.",
        )
    return session


def _get_own_worker_profile(
    worker_chat_id: int,
    db: Session,
    current_user: model.User,
) -> model.WorkerProfile:
    """Fetch the WorkerProfile behind a chat id; raise 404 if registration is incomplete."""
    profile = db.execute(
        select(model.WorkerProfile).where(
            model.WorkerProfile.worker_chat_id == worker_chat_id,
            model.WorkerProfile.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No registered worker profile found for this chat id. "
                "Finish registration with POST /worker-interview/{id}/complete first."
            ),
        )
    return profile


def _commit_or_500(db: Session) -> None:
    """Commit or roll back and raise a clean 500."""
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database write failure.",
        )


async def _get_address_from_coords(lat: float, lng: float) -> str:
    """Reverse-geocode lat/lng to a human-readable address via Nominatim."""
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"lat": lat, "lon": lng, "format": "json", "addressdetails": 1}
    headers = {"User-Agent": "WorkerVerificationApp/1.0 (contact: admin@yourdomain.com)"}

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, params=params, headers=headers, timeout=8.0)
        if r.status_code == 200:
            data = r.json()
            if "display_name" in data:
                return data["display_name"]
            logger.error("[Geocode] 'display_name' missing in Nominatim response")
        else:
            logger.error("[Geocode] Nominatim returned HTTP %s", r.status_code)
    except Exception as exc:
        logger.error("[Geocode] Network failure: %s", exc)

    return f"Location ({lat}, {lng})"


async def _broadcast_live_alerts(worker_chat_id: int, matched_jobs: list[dict]) -> None:
    """Fire-and-forget WebSocket alerts after a successful registration."""
    for job in matched_jobs:
        booking_chat_id = job.get("booking_chat_id")

        try:
            await manager.send_worker_notification(
                worker_chat_id,
                {
                    "event": "new_job_match",
                    "booking_chat_id": booking_chat_id,
                    "title": job.get("title"),
                    "description": job.get("description"),
                },
            )
        except Exception as exc:
            logger.warning("Worker alert failed (worker=%s): %s", worker_chat_id, exc)

        try:
            await manager.send_customer_notification(
                booking_chat_id,
                {
                    "event": "new_worker_match",
                    "message": "A new worker matching your job requirements just joined the platform.",
                    "worker_chat_id": worker_chat_id,
                },
            )
        except Exception as exc:
            logger.warning("Customer alert failed (booking=%s): %s", booking_chat_id, exc)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Start a new session
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Main interview chat
# ═══════════════════════════════════════════════════════════════════════════════

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


# ── 2a. Grade a scenario answer ───────────────────────────────────────────────

def _handle_scenario_answer(
    chat_session: model.WorkerInterviewSession,
    answer: str,
    db: Session,
) -> dict:
    history = list(chat_session.history)
    history.append({"role": "user", "content": answer})

    try:
        passed, score, _report = evaluate_answer(
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
        history.append({
            "role": "assistant",
            "content": (
                f"[TEST_REQUIRED: {chat_session.pending_sub_skill}]\n"
                f"System record: scenario answered. Score: {score}/100. PASS. {COMPLETE_TOKEN}"
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
        except Exception as exc:
            chat_session.profile = None
            ai_response = (
                "Technical verification complete, but we hit an internal error "
                "building your profile. Our team will finish this manually — "
                "no need to redo the interview."
            )
            logger.error(
                "[WorkerInterview] Profile extraction failed for worker_chat_id=%s: %s",
                chat_session.id, exc,
            )

        chat_session.stage = "complete"
        chat_session.is_complete = True
        chat_session.is_rejected = False

    else:
        history.append({
            "role": "assistant",
            "content": (
                f"[TEST_REQUIRED: {chat_session.pending_sub_skill}]\n"
                f"System record: scenario answered. Score: {score}/100. FAIL. {REJECTION_TOKEN}"
            ),
        })
        chat_session.history = history
        chat_session.stage = "complete"
        chat_session.is_complete = True
        chat_session.is_rejected = True
        chat_session.rejection_reason = (
            f"Scenario test failed — score {score}/100 "
            f"(required >{SCENARIO_PASS_THRESHOLD}) for '{chat_session.pending_sub_skill}'."
        )
        ai_response = (
            "Your answer did not demonstrate enough field knowledge for this role. "
            "This application cannot proceed right now."
        )

    _commit_or_500(db)

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


# ── 2b. Regular interview turn ────────────────────────────────────────────────

def _handle_interview_turn(
    chat_session: model.WorkerInterviewSession,
    message: str,
    db: Session,
) -> dict:
    history = list(chat_session.history)
    history.append({"role": "user", "content": message})
    turns_used = count_user_turns(history)

    try:
        ai_reply: str = _nvidia_client.chat.completions.create(
            model=MODEL_NAME,
            messages=history,
            temperature=0.0,
            max_tokens=200,
        ).choices[0].message.content.strip()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"NVIDIA NIM inference error: {exc}",
        )

    # ── Hard turn-cap: force a terminal decision when turns are exhausted ──
    if (
        turns_used >= MAX_PRETEST_TURNS
        and REJECTION_TOKEN not in ai_reply
        and not TEST_TOKEN_RE.search(ai_reply)
    ):
        history.append({"role": "assistant", "content": ai_reply})
        history.append({
            "role": "system",
            "content": (
                "The interview has run long. Based on everything discussed, "
                f"respond with ONLY one of: {REJECTION_TOKEN}, or "
                "[TEST_REQUIRED: <speciality, or '<job> — general competency'>]. "
                "No other text."
            ),
        })
        try:
            ai_reply = _nvidia_client.chat.completions.create(
                model=MODEL_NAME,
                messages=history,
                temperature=0.0,
                max_tokens=60,
            ).choices[0].message.content.strip()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"NVIDIA NIM inference error: {exc}",
            )

        # Final safety net: if the forced call still doesn't comply, reject.
        if REJECTION_TOKEN not in ai_reply and not TEST_TOKEN_RE.search(ai_reply):
            ai_reply = REJECTION_TOKEN

    # ── Route on the terminal signal ──────────────────────────────────────
    if REJECTION_TOKEN in ai_reply:
        history.append({"role": "assistant", "content": ai_reply})
        chat_session.history = history
        chat_session.stage = "complete"
        chat_session.is_complete = True
        chat_session.is_rejected = True
        chat_session.rejection_reason = "Did not meet minimum interview requirements."
        _commit_or_500(db)

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
        _commit_or_500(db)

        ai_response = (
            (visible_reply + "\n\n" + scenario).strip() if visible_reply else scenario
        )
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

    # ── Ordinary mid-interview message ────────────────────────────────────
    display = ai_reply.replace(COMPLETE_TOKEN, "").strip()
    history.append({"role": "assistant", "content": display})
    chat_session.history = history
    _commit_or_500(db)

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


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Conversation history
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Structured summary
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Complete registration & run matching engine
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{worker_chat_id}/complete",
    summary="Finalise onboarding, embed skills, geocode location, run matching engine",
)
async def complete_worker_chat(
    worker_chat_id: int,
    payload: schema.WorkerCompleteChatIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    logger.info("Starting registration pipeline for worker_chat_id=%s", worker_chat_id)

    chat_session = _get_own_worker_session(worker_chat_id, db, current_user)

    if not chat_session.is_complete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot complete registration. The AI chat session is not finished yet.",
        )

    profile_data = chat_session.profile or {}
    job_desc = (profile_data.get("job_description") or "").strip()
    if not job_desc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description is missing from the extracted profile.",
        )

    # Older profiles lack a separate baseline_description; fall back gracefully.
    baseline_desc = (profile_data.get("baseline_description") or "").strip() or job_desc
    speciality_title = (profile_data.get("speciality_title") or "").strip()
    speciality_desc = (profile_data.get("speciality_description") or "").strip()

    lat = payload.location.latitude
    lng = payload.location.longitude
    wkt_point = f"POINT({lng} {lat})"

    # Baseline embedding is mandatory — a failure here blocks registration.
    try:
        baseline_vector = await get_worker_description_embedding(baseline_desc)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Nvidia embedding API error: {exc}",
        )

    # Speciality embedding is best-effort; row is stored unvectorised on failure.
    speciality_vector = None
    if speciality_desc:
        try:
            speciality_vector = await get_worker_description_embedding(speciality_desc)
        except Exception as exc:
            logger.error(
                "Speciality embedding failed for worker_chat_id=%s (%s); "
                "storing row unvectorised.",
                worker_chat_id, exc,
            )

    address_text = await _get_address_from_coords(lat, lng)

    db_profile = db.query(model.WorkerProfile).filter(
        model.WorkerProfile.worker_chat_id == worker_chat_id,
        model.WorkerProfile.user_id == current_user.id,
    ).first()

    core_fields = {
        "stage": "pending_admin_review",
        "is_complete": False,
        "is_rejected": chat_session.is_rejected,
        "rejection_reason": chat_session.rejection_reason,
        "latitude": lat,
        "longitude": lng,
        "location": wkt_point,
        "phone_number": payload.phone_number,
        "address_text": address_text,
    }

    if db_profile:
        for key, value in core_fields.items():
            setattr(db_profile, key, value)
        sync_profile_extracted_fields(db_profile, profile_data)
    else:
        db_profile = model.WorkerProfile(
            user_id=current_user.id,
            worker_chat_id=worker_chat_id,
            **core_fields,
        )
        sync_profile_extracted_fields(db_profile, profile_data)
        db.add(db_profile)

    # Legacy field kept populated so older diagnostics/readers keep working.
    db_profile.description_vector = baseline_vector

    db.flush()  # obtain db_profile.id before writing skill FKs

    upsert_baseline_skill(
        db=db,
        worker_id=db_profile.id,
        title=db_profile.job_category or "general work",
        description=baseline_desc,
        embedding=baseline_vector,
    )

    if speciality_desc:
        upsert_speciality_skill(
            db=db,
            worker_id=db_profile.id,
            title=speciality_title or (chat_session.pending_sub_skill or "speciality"),
            description=speciality_desc,
            embedding=speciality_vector,
            scenario_question=chat_session.pending_scenario,
            scenario_score=chat_session.scenario_score,
        )

    db.flush()

    try:
        matching_result = matching_manager.create_matches_for_worker(
            db=db,
            worker_id=db_profile.id,
            worker_location=wkt_point,
            radius_meters=DEFAULT_SEARCH_RADIUS_METERS,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Matching engine failure for worker_chat_id=%s: %s", worker_chat_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run the matching engine after registration.",
        )

    matched_jobs = matching_result.get("matched_jobs", [])
    if matched_jobs:
        background_tasks.add_task(_broadcast_live_alerts, worker_chat_id, matched_jobs)

    return {
        "status": "success",
        "message": (
            f"Worker profile activated. "
            f"Pre-calculated matches created for {matching_result.get('count', 0)} open jobs."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 6. List skills
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{worker_chat_id}/skills",
    response_model=schema.WorkerSkillsListOut,
    summary="List the worker's independently matchable skills",
)
def list_worker_skills(
    worker_chat_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    db_profile = _get_own_worker_profile(worker_chat_id, db, current_user)

    skills = db.execute(
        select(model.WorkerSkill)
        .where(model.WorkerSkill.worker_id == db_profile.id)
        .order_by(model.WorkerSkill.skill_type.asc(), model.WorkerSkill.created_at.asc())
    ).scalars().all()

    return {
        "worker_chat_id": worker_chat_id,
        "worker_id": db_profile.id,
        "job_category": db_profile.job_category,
        "skills": [
            {
                "id": s.id,
                "skill_type": (
                    s.skill_type.value if hasattr(s.skill_type, "value") else str(s.skill_type)
                ),
                "title": s.title,
                "description": s.description,
                "scenario_score": s.scenario_score,
                "is_active": s.is_active,
                "has_vector": s.embedding is not None,
            }
            for s in skills
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Start adding a speciality
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{worker_chat_id}/add-skill",
    response_model=schema.AddSkillStartOut,
    summary="Begin adding another speciality to an existing verified profile",
)
def start_add_skill(
    worker_chat_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    chat_session = _get_own_worker_session(worker_chat_id, db, current_user)
    db_profile = _get_own_worker_profile(worker_chat_id, db, current_user)

    if chat_session.is_rejected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A rejected application cannot add specialities.",
        )

    # Start completely clean so a previous abandoned attempt cannot bleed in.
    chat_session.add_skill_turns = []
    chat_session.stage = "adding_skill"
    chat_session.pending_sub_skill = None
    chat_session.pending_scenario = None
    _commit_or_500(db)

    return {
        "worker_chat_id": worker_chat_id,
        "ai_response": ADD_SKILL_GREETING,
        "existing_skills": active_skill_titles(db, db_profile.id),
        "stage": "adding_skill",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Add-skill conversation turn
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{worker_chat_id}/add-skill/chat",
    response_model=schema.AddSkillMessageOut,
    summary="Send one message in the add-speciality conversation",
)
async def add_skill_chat(
    worker_chat_id: int,
    payload: schema.AddSkillMessageIn,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    chat_session = _get_own_worker_session(worker_chat_id, db, current_user)
    db_profile = _get_own_worker_profile(worker_chat_id, db, current_user)

    if chat_session.stage not in ("adding_skill", "awaiting_skill_scenario"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Not currently in an add-skill flow. "
                "Call POST /worker-interview/{id}/add-skill first."
            ),
        )

    turns = list(chat_session.add_skill_turns or [])
    turns.append({"role": "user", "content": payload.message.strip()})

    # ── Branch: grading a scenario answer ────────────────────────────────
    if chat_session.stage == "awaiting_skill_scenario":
        return await _handle_add_skill_scenario_answer(
            chat_session, db_profile, turns, payload.message.strip(), db,
        )

    # ── Branch: deciding whether the claim warrants a test ────────────────
    existing = active_skill_titles(db, db_profile.id)
    messages = _build_add_skill_messages(db_profile.job_category, existing, turns)

    try:
        raw_reply: str = _nvidia_client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.0,
            max_tokens=120,
        ).choices[0].message.content.strip()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"NVIDIA NIM inference error: {exc}",
        )

    logger.debug(
        "[add-skill] worker_chat_id=%s raw_reply=%r",
        worker_chat_id, raw_reply,
    )

    signal, sub_skill = _parse_add_skill_signal(raw_reply)

    # Hard cap: if the model is still asking questions after 3 user turns,
    # force a rejection. The prompt asks for 1 follow-up; 3 is generous.
    user_turns_so_far = sum(1 for t in turns if t.get("role") == "user")
    if signal == "message" and user_turns_so_far >= 3:
        logger.warning(
            "[add-skill] Forcing rejection after %d user turns without decision "
            "(worker_chat_id=%s).",
            user_turns_so_far, worker_chat_id,
        )
        signal = "rejected"

    # ── REJECTED ──────────────────────────────────────────────────────────
    if signal == "rejected":
        chat_session.add_skill_turns = turns
        chat_session.stage = "skill_declined"
        _commit_or_500(db)
        return {
            "worker_chat_id": worker_chat_id,
            "ai_response": (
                "No new speciality was added. "
                "Your existing profile and verified skills are unchanged."
            ),
            "stage": "skill_declined",
            "scenario_question": None,
            "skill_added": False,
        }

    # ── TEST REQUIRED ─────────────────────────────────────────────────────
    if signal == "test" and sub_skill:
        # Guard: a general-competency test adds nothing for an already-verified worker.
        if is_general_competency_test(sub_skill):
            chat_session.add_skill_turns = turns
            chat_session.stage = "skill_declined"
            _commit_or_500(db)
            return {
                "worker_chat_id": worker_chat_id,
                "ai_response": (
                    "That is standard work for your trade, which your profile "
                    "already covers. No new speciality was added."
                ),
                "stage": "skill_declined",
                "scenario_question": None,
                "skill_added": False,
            }

        try:
            scenario = generate_scenario(sub_skill, MODEL_NAME)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"NVIDIA NIM scenario generation error: {exc}",
            )

        turns.append({"role": "assistant", "content": raw_reply})
        chat_session.add_skill_turns = turns
        chat_session.stage = "awaiting_skill_scenario"
        chat_session.pending_sub_skill = sub_skill
        chat_session.pending_scenario = scenario
        _commit_or_500(db)

        return {
            "worker_chat_id": worker_chat_id,
            "ai_response": scenario,
            "stage": "awaiting_skill_scenario",
            "scenario_question": scenario,
            "skill_added": False,
        }

    # ── Ordinary follow-up question ───────────────────────────────────────
    display = raw_reply.replace(COMPLETE_TOKEN, "").strip()
    turns.append({"role": "assistant", "content": display})
    chat_session.add_skill_turns = turns
    _commit_or_500(db)

    return {
        "worker_chat_id": worker_chat_id,
        "ai_response": display,
        "stage": "adding_skill",
        "scenario_question": None,
        "skill_added": False,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 8a. Grade an add-skill scenario answer
# ═══════════════════════════════════════════════════════════════════════════════

async def _handle_add_skill_scenario_answer(
    chat_session: model.WorkerInterviewSession,
    db_profile: model.WorkerProfile,
    turns: list[dict],
    answer: str,
    db: Session,
) -> dict:
    """
    Grade the scenario, and on a pass append exactly one new speciality row.

    A failure here is intentionally cost-free to the worker: their profile,
    baseline skill, and all existing specialities are untouched. The downside
    of a failed add-skill test is "no new skill", never "lost existing standing".
    """
    sub_skill = chat_session.pending_sub_skill or ""
    scenario = chat_session.pending_scenario or ""

    try:
        passed, score, _report = evaluate_answer(
            sub_skill=sub_skill,
            scenario=scenario,
            answer=answer,
            model_name=MODEL_NAME,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"NVIDIA NIM evaluation error: {exc}",
        )

    turns.append({
        "role": "assistant",
        "content": (
            f"System record: add-skill scenario for '{sub_skill}' answered. "
            f"Score: {score}/100. Result: {'PASS' if passed else 'FAIL'}."
        ),
    })
    chat_session.add_skill_turns = turns
    chat_session.scenario_score = score
    chat_session.scenario_passed = passed

    # ── FAIL ──────────────────────────────────────────────────────────────
    if not passed:
        chat_session.stage = "skill_declined"
        chat_session.pending_sub_skill = None
        chat_session.pending_scenario = None
        _commit_or_500(db)
        return {
            "worker_chat_id": chat_session.id,
            "ai_response": (
                f"That answer scored {score}/100, below the {SCENARIO_PASS_THRESHOLD} "
                "needed to verify this speciality. Your existing profile and "
                "verified skills are unchanged."
            ),
            "stage": "skill_declined",
            "scenario_question": None,
            "skill_added": False,
            "scenario_score": score,
        }

    # ── PASS — build description, embed, persist ──────────────────────────
    try:
        description = generate_speciality_description(
            sub_skill=sub_skill,
            scenario=scenario,
            answer=answer,
            job_category=db_profile.job_category or "",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not generate a description for the new speciality: {exc}",
        )

    # Embedding failure is surfaced (unlike at registration) because the entire
    # purpose of this call was to produce a matchable skill row.
    skill_vector = None
    try:
        skill_vector = await get_worker_description_embedding(description)
    except Exception as exc:
        logger.error(
            "Embedding failed for new speciality %r on worker_id=%s (%s); "
            "row stored unvectorised.",
            sub_skill, db_profile.id, exc,
        )

    upsert_speciality_skill(
        db=db,
        worker_id=db_profile.id,
        title=sub_skill,
        description=description,
        embedding=skill_vector,
        scenario_question=scenario,
        scenario_answer=answer,
        scenario_score=score,
    )

    # Keep the parent profile's human-readable fields consistent.
    db_profile.has_verified_specialty = True
    if description and description.lower() not in (db_profile.job_description or "").lower():
        db_profile.job_description = (
            f"{(db_profile.job_description or '').rstrip('.')}. {description}".strip()
        )

    chat_session.stage = "skill_complete"
    chat_session.pending_sub_skill = None
    chat_session.pending_scenario = None
    _commit_or_500(db)

    # Re-run matching so the new skill is applied to jobs already on the
    # marketplace (not just future ones). Non-fatal — skill is already stored.
    if skill_vector is not None and db_profile.is_complete and db_profile.location is not None:
        try:
            matching_manager.create_matches_for_worker(
                db=db,
                worker_id=db_profile.id,
                worker_location=db_profile.location,
                radius_meters=DEFAULT_SEARCH_RADIUS_METERS,
            )
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.error(
                "Re-match after add-skill for worker_id=%s failed: %s",
                db_profile.id, exc,
            )

    vector_note = (
        "" if skill_vector
        else " It is saved but will start matching once its vector is generated."
    )
    return {
        "worker_chat_id": chat_session.id,
        "ai_response": (
            f"Verified — scored {score}/100. "
            f"'{sub_skill}' has been added to your profile as a new speciality.{vector_note}"
        ),
        "stage": "skill_complete",
        "scenario_question": None,
        "skill_added": True,
        "skill_title": sub_skill,
        "scenario_score": score,
    }