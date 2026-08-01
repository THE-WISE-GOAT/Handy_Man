import os
import json
import math
import logging
from typing import TypedDict, Any
from openai import OpenAI
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from src.core import model
from src.core.schema import MatchingResult, MatchDetail, WorkerMatchingResult, MatchedJobDetail
from dotenv import load_dotenv

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


def _ensure_geography(location: Any):
    """
    Safely normalizes dictionaries, Pydantic objects, or GeoAlchemy elements 
    into a valid PostGIS Geography Point with guaranteed (Longitude, Latitude) order.
    """
    if isinstance(location, WKBElement):
        return location

    lat, lon = None, None

    # Handle Pydantic models or objects with attribute lookup
    if hasattr(location, "latitude") and hasattr(location, "longitude"):
        lat, lon = location.latitude, location.longitude
    # Handle dictionary payloads
    elif isinstance(location, dict):
        lat = location.get("latitude") or location.get("lat")
        lon = location.get("longitude") or location.get("lng") or location.get("lon")

    if lat is not None and lon is not None:
        # PostGIS ST_MakePoint REQUIRES Longitude (X) FIRST, Latitude (Y) SECOND
        return func.ST_SetSRID(
            func.ST_MakePoint(float(lon), float(lat)), 
            4326
        ).cast(Geography)

    return location


def _search_workers(
    db: Session,
    query_vector: list[float],
    customer_location: Any,
    radius_meters: int,
) -> list[tuple[model.WorkerProfile, model.User, model.WorkerSkill, float]]:
    """
    Vector search against each active worker capability (WorkerSkill.embedding).
    Each worker capability is stored as its own row so matching selects the
    worker's best-fitting skill rather than an averaged profile vector.
    """
    distance_expr = model.WorkerSkill.embedding.cosine_distance(query_vector)
    spatial_point = _ensure_geography(customer_location)

    stmt = (
        select(
            model.WorkerProfile,
            model.User,
            model.WorkerSkill,
            distance_expr.label("distance"),
        )
        .join(model.WorkerSkill, model.WorkerSkill.worker_id == model.WorkerProfile.id)
        .join(model.User, model.User.id == model.WorkerProfile.user_id)
        .where(
            model.WorkerSkill.embedding.isnot(None),
            model.WorkerSkill.is_active.is_(True),
            model.WorkerProfile.location.isnot(None),
            model.WorkerProfile.is_complete.is_(True),
            model.WorkerProfile.is_rejected.is_(False),
            func.ST_DWithin(model.WorkerProfile.location, spatial_point, radius_meters),
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
    search_results: list[tuple[model.WorkerProfile, model.User, model.WorkerSkill, float]]
) -> list[tuple[model.WorkerProfile, model.User, model.WorkerSkill, float]]:
    """
    Deduplicates results by human user (User.id or WorkerProfile.user_id).
    Since search_results are ordered best-distance-first (distance.asc()),
    the first occurrence of a user preserves that person's single highest-scoring
    match across all their profiles and skills.
    """
    seen_user_ids: set[int] = set()
    deduped: list[tuple[model.WorkerProfile, model.User, model.WorkerSkill, float]] = []

    for worker, user, skill, distance in search_results:
        user_key = getattr(user, "id", None) or getattr(worker, "user_id", None) or worker.id

        if user_key in seen_user_ids:
            continue

        seen_user_ids.add(user_key)
        deduped.append((worker, user, skill, distance))

    return deduped


def _build_candidate_summary(match: MatchDetail) -> dict:
    """Lightweight, text-only view of a candidate for the reranker prompt."""
    worker = match["worker_profile"]
    return {
        "worker_id": worker.id,
        "vector_rank": match["rank"],
        "vector_score": match["score"],
        "job_category": worker.job_category,
        "category_tag": worker.category_tag,
        "matched_skill_title": match.get("matched_skill_title"),
        "matched_skill_description": match.get("matched_skill_description"),
        "profile_summary": worker.job_description,
    }


def _llm_rerank_matches(
    job_description: str,
    job_category: str | None,
    rich_matches: list[MatchDetail],
) -> list[MatchDetail]:
    """
    Final decision step: hands the vector-qualified, per-user-deduplicated candidates to an
    LLM to drop candidates whose trade or skill doesn't fit the actual job requirements.
    """
    if not rich_matches:
        logger.info("No candidate matches passed to LLM reranker.")
        return rich_matches

    candidates = rich_matches[:MAX_CANDIDATES_FOR_RERANK]
    leftover = rich_matches[MAX_CANDIDATES_FOR_RERANK:]

    candidate_payload = [_build_candidate_summary(m) for m in candidates]

    prompt = (
        "You are the final filter deciding which tradespeople genuinely fit a customer's job.\n\n"
        f"Job category (as identified by the intake system): {job_category or 'unknown'}\n"
        f"Job description:\n{job_description}\n\n"
        f"Candidates (JSON):\n{json.dumps(candidate_payload)}\n\n"
        "Each candidate has a vector_score from semantic text similarity, but that score alone is "
        "NOT reliable for trade fit — e.g. an electrician or a cleaner can score highly similar to a "
        "plumbing job just because both descriptions use words like 'fix', 'repair', or 'install'.\n\n"
        "Only keep candidates whose actual trade and specific skills (job_category / category_tag / matched_skill_title / profile_summary) "
        "can genuinely perform this specific job. Drop anyone from a different trade, no matter how high "
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
        if isinstance(parsed_ids, dict):
            parsed_ids = next((v for v in parsed_ids.values() if isinstance(v, list)), [])

        if isinstance(parsed_ids, list):
            ordered_ids = [int(x) for x in parsed_ids if isinstance(x, (int, str)) and str(x).isdigit()]
        else:
            ordered_ids = []

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

    for i, match in enumerate(leftover, start=len(reranked) + 1):
        match["rank"] = i

    return reranked + leftover


def create_matches_for_job(
    db: Session,
    job_id: int,
    query_vector: list[float],
    customer_location: Any,
    radius_meters: int,
    job_description: str,
    job_category: str | None = None,
) -> MatchingResult:
    """
    Core Entry Point: Purges stale matches, queries per-skill vector embeddings,
    deduplicates down to the best skill per user, scores, filters by threshold,
    reranks via LLM, and persists final match rows with matched_skill_id.
    """
    logger.info(
        f"[job {job_id}] starting match run — radius_meters={radius_meters}, "
        f"job_category={job_category}, query_vector_len={len(query_vector) if query_vector else 0}"
    )

    # 1. Clear historical stale match rows for this job
    db.query(model.JobWorkerMatch).filter(
        model.JobWorkerMatch.job_id == job_id
    ).delete(synchronize_session=False)

    # 2. Extract potential candidate skills (ordered by distance)
    search_results = _search_workers(db, query_vector, customer_location, radius_meters)
    logger.info(f"[job {job_id}] _search_workers returned {len(search_results)} candidate skill matches")

    search_results = _deduplicate_by_user(search_results)
    logger.info(f"[job {job_id}] {len(search_results)} candidates remain after per-user dedup")

    rich_matches: list[MatchDetail] = []
    distance_by_worker_id: dict[int, float] = {}
    vector_rank = 1

    for worker, user, skill, distance in search_results:
        score = calculate_match_score(float(distance))

        logger.info(
            f"[job {job_id}] candidate worker_id={worker.id} category={worker.job_category} "
            f"matched_skill='{skill.title}' distance={float(distance):.4f} score={score} (threshold={SCORE_THRESHOLD})"
        )

        if score > SCORE_THRESHOLD:
            rich_matches.append({
                "worker_profile": worker,
                "user": user,
                "score": score,
                "rank": vector_rank,
                "worker_chat_id": worker.worker_chat_id,
                "matched_skill_id": skill.id,
                "matched_skill_title": skill.title,
                "matched_skill_description": skill.description,
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
            matched_skill_id=match.get("matched_skill_id"),
            match_score=match["score"],
            match_rank=match["rank"],
            semantic_distance=distance_by_worker_id[worker.id],
            is_active=True,
            is_interested=False,
            is_selected=False,
            is_rejected=False,
        )
        new_match_records.append(match_row)
        notifiable_worker_chat_ids.append(match["worker_chat_id"])

    if new_match_records:
        db.add_all(new_match_records)
        db.flush()

    return {
        "matches": rich_matches,
        "worker_chat_ids": notifiable_worker_chat_ids,
        "count": len(rich_matches),
    }


def create_matches_for_worker(
    db: Session,
    worker_id: int,
    worker_location: Any,
    radius_meters: int = 60_000,
) -> WorkerMatchingResult:
    """
    Reverse Job Matching Entry Point: Compares all active pending jobs against
    all active skill embeddings for this worker, keeping the best matching skill
    per job.
    """
    logger.info(f"Running reverse matching pipeline for worker_id: {worker_id}")

    # 1. Clear out historical stale match rows for this worker
    db.query(model.JobWorkerMatch).filter(
        model.JobWorkerMatch.worker_id == worker_id
    ).delete(synchronize_session=False)

    # 2. Match active jobs against any active skill vector owned by this worker
    distance_expr = model.Job.description_vector.cosine_distance(model.WorkerSkill.embedding)
    spatial_point = _ensure_geography(worker_location)

    stmt = (
        select(
            model.Job,
            model.WorkerSkill,
            distance_expr.label("distance"),
        )
        .join(model.WorkerSkill, model.WorkerSkill.worker_id == worker_id)
        .where(
            model.WorkerSkill.is_active.is_(True),
            model.WorkerSkill.embedding.isnot(None),
            model.Job.description_vector.isnot(None),
            model.Job.location.isnot(None),
            model.Job.status == "pending",
            func.ST_DWithin(model.Job.location, spatial_point, radius_meters),
        )
        .order_by(distance_expr.asc())
    )

    search_results = db.execute(stmt).all()

    seen_job_ids: set[int] = set()
    new_match_records = []
    matched_jobs_payload: list[MatchedJobDetail] = []
    current_rank = 1

    for job, skill, distance in search_results:
        # Deduplicate to preserve only the best skill fit per job
        if job.id in seen_job_ids:
            continue
        seen_job_ids.add(job.id)

        score = calculate_match_score(float(distance))

        if score > SCORE_THRESHOLD:
            match_row = model.JobWorkerMatch(
                job_id=job.id,
                worker_id=worker_id,
                matched_skill_id=skill.id,
                match_score=score,
                match_rank=current_rank,
                semantic_distance=float(distance),
                is_active=True,
                is_interested=False,
                is_selected=False,
                is_rejected=False,
            )
            new_match_records.append(match_row)

            matched_jobs_payload.append({
                "booking_chat_id": job.booking_chat_id,
                "title": job.title,
                "description": job.description,
                "score": score,
                "rank": current_rank,
                "matched_skill_title": skill.title,
            })
            current_rank += 1

    if new_match_records:
        db.add_all(new_match_records)
        db.flush()

    return {
        "matched_jobs": matched_jobs_payload,
        "count": len(matched_jobs_payload),
    }