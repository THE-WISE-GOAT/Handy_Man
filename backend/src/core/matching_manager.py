import os
import json
import math
import logging
from typing import TypedDict, Any
from openai import OpenAI
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from src.core import model
from src.core.schema import MatchingResult, MatchDetail, WorkerMatchingResult, MatchedJobDetail
from dotenv import load_dotenv  # 1. Add this import

# 2. Force load the environment variables from your local config files
load_dotenv()

logger = logging.getLogger(__name__)

SCORE_THRESHOLD = 70

# --- LLM reranker config ---
_nvidia_client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY"),
)
RERANK_MODEL = "meta/llama-3.1-8b-instruct"
MAX_CANDIDATES_FOR_RERANK = 25  # keep the prompt bounded no matter how many clear threshold


def _search_workers(
    db: Session,
    query_vector: list[float],
    customer_location,
    radius_meters: int,
) -> list[tuple[model.WorkerProfile, model.User, float]]:
    """
    Vector search against each worker's profile-level embedding
    (WorkerProfile.description_vector).

    NOTE: WorkerExpertise (per-skill vectors) is not populated anywhere in the
    current write path, so matching cannot depend on it. This queries the one
    embedding that actually exists per worker today.
    """
    distance_expr = model.WorkerProfile.description_vector.cosine_distance(query_vector)

    stmt = (
        select(model.WorkerProfile, model.User, distance_expr.label("distance"))
        .join(model.User, model.User.id == model.WorkerProfile.user_id)
        .where(
            model.WorkerProfile.description_vector.isnot(None),
            model.WorkerProfile.location.isnot(None),
            model.WorkerProfile.is_complete.is_(True),
            model.WorkerProfile.is_rejected.is_(False),
            func.ST_DWithin(model.WorkerProfile.location, customer_location, radius_meters),
        )
        .order_by(distance_expr.asc())
    )

    return db.execute(stmt).all()


def calculate_match_score(distance: float) -> float:
    """The system's single source of truth scoring mechanism (Sigmoid)."""
    try:
        return max(0.0, min(100.0, round((1.0 / (1.0 + math.exp(25.0 * (distance - 0.90)))) * 100.0, 2)))
    except Exception:
        return 0.0


def _deduplicate_by_user(
    search_results: list[tuple[model.WorkerProfile, model.User, float]]
) -> list[tuple[model.WorkerProfile, model.User, float]]:
    """
    Safety net, not currently load-bearing: WorkerProfile.user_id is unique in the
    schema, so a user can only ever have one profile today. Kept in case that
    constraint is ever relaxed — search_results is already best-distance-first,
    so the first occurrence of a user_id is always the one to keep.
    """
    seen_user_ids: set[int] = set()
    deduped: list[tuple[model.WorkerProfile, model.User, float]] = []

    for worker, user, distance in search_results:
        if user.id in seen_user_ids:
            continue
        seen_user_ids.add(user.id)
        deduped.append((worker, user, distance))

    return deduped


def _build_candidate_summary(worker: model.WorkerProfile, score: float, rank: int) -> dict:
    """Lightweight, text-only view of a candidate for the reranker prompt."""
    return {
        "worker_id": worker.id,
        "vector_rank": rank,
        "vector_score": score,
        "job_category": worker.job_category,
        "category_tag": worker.category_tag,
        "profile_summary": worker.job_description,
    }


def _llm_rerank_matches(
    job_description: str,
    job_category: str | None,
    rich_matches: list[MatchDetail],
) -> list[MatchDetail]:
    """
    Final decision step: the vector search ranks by semantic similarity, which
    conflates "this text talks about fixing/repairing things" with "this trade
    can actually do this job" — an electrician or a cleaner can score highly
    against a plumbing description just from shared repair-ish vocabulary.

    This step hands the vector-qualified, per-user-deduplicated candidates to an
    LLM whose job is specifically to DROP anyone whose actual trade doesn't fit,
    regardless of how high their vector_score was.

    Fails open: any error/unparsable response falls back to the unfiltered vector
    order, so a reranker outage never blocks matching entirely — the tradeoff is
    that a temporary LLM failure means mismatched trades could slip through for
    that one request rather than the whole pipeline going down.
    """
    if not rich_matches:
        logger.info("No candidate matches passed to LLM reranker.")
        return rich_matches

    candidates = rich_matches[:MAX_CANDIDATES_FOR_RERANK]
    leftover = rich_matches[MAX_CANDIDATES_FOR_RERANK:]

    candidate_payload = [
        _build_candidate_summary(m["worker_profile"], m["score"], m["rank"])
        for m in candidates
    ]

    prompt = (
        "You are the final filter deciding which tradespeople genuinely fit a customer's job.\n\n"
        f"Job category (as identified by the intake system): {job_category or 'unknown'}\n"
        f"Job description:\n{job_description}\n\n"
        f"Candidates (JSON):\n{json.dumps(candidate_payload)}\n\n"
        "Each candidate has a vector_score from semantic text similarity, but that score alone is "
        "NOT reliable for trade fit — e.g. an electrician or a cleaner can score highly similar to a "
        "plumbing job just because both descriptions use words like 'fix', 'repair', or 'install'.\n\n"
        "Only keep candidates whose actual trade (job_category / category_tag / profile_summary) can "
        "genuinely perform this specific job. Drop anyone from a different trade, no matter how high "
        "their vector_score is.\n\n"
        "Return ONLY a JSON array of the worker_id integers you are keeping, ordered best fit first. "
        "No text outside the JSON array."
    )

    try:
        response = _nvidia_client.chat.completions.create(
            model=RERANK_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = (response.choices[0].message.content or "").strip()
        raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        parsed_ids = json.loads(raw_text)
        ordered_ids = [int(x) for x in parsed_ids if isinstance(x, (int, str)) and str(x).isdigit()]
        logger.info(f"LLM reranker kept {len(ordered_ids)}/{len(candidates)} candidates: {ordered_ids}")

    except Exception as e:
        logger.error(f"LLM reranker failed, falling back to unfiltered vector order: {e}")
        return rich_matches

    by_worker_id = {int(m["worker_profile"].id): m for m in candidates}
    reranked: list[MatchDetail] = []
    seen_ids: set[int] = set()

    for new_rank, worker_id in enumerate(ordered_ids, start=1):
        match = by_worker_id.get(worker_id)
        if match is None or worker_id in seen_ids:
            continue
        match["rank"] = new_rank
        reranked.append(match)
        seen_ids.add(worker_id)

    if not reranked:
        logger.warning("LLM reranker kept zero candidates — falling back to unfiltered vector order.")
        return rich_matches

    # Candidates beyond MAX_CANDIDATES_FOR_RERANK were never shown to the LLM at all;
    # keep them (unfiltered) after the reranked set rather than silently dropping them.
    # Anyone the LLM explicitly excluded is NOT re-added here — that's the whole point.
    for i, match in enumerate(leftover, start=len(reranked) + 1):
        match["rank"] = i

    return reranked + leftover


def create_matches_for_job(
    db: Session,
    job_id: int,
    query_vector: list[float],
    customer_location,
    radius_meters: int,
    job_description: str,
    job_category: str | None = None,
) -> MatchingResult:
    """
    Core Entry Point: Purges stale matches, dedupes candidates down to one profile per
    user, scores + threshold-filters, sends the survivors to the LLM reranker to drop
    trade mismatches and make the final call, then persists and flushes the matches.
    """
    logger.info(
        f"[job {job_id}] starting match run — radius_meters={radius_meters}, "
        f"job_category={job_category}, query_vector_len={len(query_vector) if query_vector else 0}"
    )

    # 1. Clear historical stale match rows for this job
    db.query(model.JobWorkerMatch).filter(
        model.JobWorkerMatch.job_id == job_id
    ).delete(synchronize_session=False)

    # 2. Extract potential candidate profiles (ordered by distance)
    search_results = _search_workers(db, query_vector, customer_location, radius_meters)
    logger.info(f"[job {job_id}] _search_workers returned {len(search_results)} candidate profiles")

    search_results = _deduplicate_by_user(search_results)
    logger.info(f"[job {job_id}] {len(search_results)} candidates remain after per-user dedup")

    rich_matches: list[MatchDetail] = []
    distance_by_worker_id: dict[int, float] = {}
    vector_rank = 1

    for worker, user, distance in search_results:
        score = calculate_match_score(float(distance))

        logger.info(
            f"[job {job_id}] candidate worker_id={worker.id} category={worker.job_category} "
            f"distance={float(distance):.4f} score={score} (threshold={SCORE_THRESHOLD})"
        )

        if score > SCORE_THRESHOLD:
            rich_matches.append({
                "worker_profile": worker,
                "user": user,
                "score": score,
                "rank": vector_rank,
                "worker_chat_id": worker.worker_chat_id
            })
            distance_by_worker_id[worker.id] = float(distance)
            vector_rank += 1

    logger.info(f"[job {job_id}] {len(rich_matches)} candidates cleared SCORE_THRESHOLD={SCORE_THRESHOLD}")

    # 3. LLM makes the final trade-fit decision
    rich_matches = _llm_rerank_matches(job_description, job_category, rich_matches)
    logger.info(f"[job {job_id}] {len(rich_matches)} candidates remain after LLM reranker")

    # 4. Persist the final match set
    new_match_records = []
    notifiable_worker_chat_ids = []

    for match in rich_matches:
        worker = match["worker_profile"]
        match_row = model.JobWorkerMatch(
            job_id=job_id,
            worker_id=worker.id,
            match_score=match["score"],
            match_rank=match["rank"],
            semantic_distance=distance_by_worker_id[worker.id],
            is_active=True,
            is_interested=False,
            is_selected=False,
            is_rejected=False
        )
        new_match_records.append(match_row)
        notifiable_worker_chat_ids.append(match["worker_chat_id"])

    if new_match_records:
        db.add_all(new_match_records)
        db.flush()

    return {
        "matches": rich_matches,
        "worker_chat_ids": notifiable_worker_chat_ids,
        "count": len(rich_matches)
    }


def create_matches_for_worker(
    db: Session,
    worker_id: int,
    worker_location,
    radius_meters: int = 60_000
) -> WorkerMatchingResult:
    """
    Reverse Job Matching Entry Point: Compares all active pending jobs against this
    worker's single profile-level embedding.
    """
    logger.info(f"Running reverse matching pipeline for worker_id: {worker_id}")

    # 1. Clear out historical stale match rows for this worker
    db.query(model.JobWorkerMatch).filter(
        model.JobWorkerMatch.worker_id == worker_id
    ).delete(synchronize_session=False)

    # 2. Fetch this worker's single profile-level embedding
    worker_profile = db.execute(
        select(model.WorkerProfile).where(model.WorkerProfile.id == worker_id)
    ).scalar_one_or_none()

    if worker_profile is None or worker_profile.description_vector is None:
        logger.warning(f"Worker {worker_id} has no profile / no description_vector — skipping reverse match.")
        return {"matched_jobs": [], "count": 0}

    distance_expr = model.Job.description_vector.cosine_distance(worker_profile.description_vector)

    stmt = (
        select(model.Job, distance_expr.label("distance"))
        .where(
            model.Job.description_vector.isnot(None),
            model.Job.location.isnot(None),
            model.Job.status == "pending",
            func.ST_DWithin(model.Job.location, worker_location, radius_meters),
        )
        .order_by(distance_expr.asc())
    )

    search_results = db.execute(stmt).all()

    new_match_records = []
    matched_jobs_payload: list[MatchedJobDetail] = []
    current_rank = 1

    for job, distance in search_results:
        score = calculate_match_score(float(distance))

        if score > SCORE_THRESHOLD:
            match_row = model.JobWorkerMatch(
                job_id=job.id,
                worker_id=worker_id,
                match_score=score,
                match_rank=current_rank,
                semantic_distance=float(distance),
                is_active=True,
                is_interested=False,
                is_selected=False,
                is_rejected=False
            )
            new_match_records.append(match_row)

            matched_jobs_payload.append({
                "booking_chat_id": job.booking_chat_id,
                "title": job.title,
                "description": job.description,
                "score": score,
                "rank": current_rank
            })
            current_rank += 1

    if new_match_records:
        db.add_all(new_match_records)
        db.flush()

    return {
        "matched_jobs": matched_jobs_payload,
        "count": len(matched_jobs_payload)
    }