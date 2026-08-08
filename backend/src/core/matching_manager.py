import os
import re
import json
import math
import logging
from typing import Any, Optional
from openai import OpenAI
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from src.core import model
from src.core.schema import (
    MatchingResult,
    MatchDetail,
    WorkerMatchingResult,
    MatchedJobDetail,
)
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SCORE_THRESHOLD = 70.0
RERANK_MODEL = "meta/llama-3.1-8b-instruct"
MAX_CANDIDATES_FOR_RERANK = 25


def _get_nvidia_client() -> OpenAI:
    """Lazy initializer for OpenAI client using Nvidia endpoint."""
    return OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ.get("NVIDIA_API_KEY"),
    )


def _ensure_geography(location: Any):
    """
    Safely normalizes dictionaries, Pydantic objects, or GeoAlchemy elements
    into a valid PostGIS Geography Point with guaranteed (Longitude, Latitude) order.
    """
    if location is None or isinstance(location, WKBElement):
        return location

    lat, lon = None, None

    if hasattr(location, "latitude") and hasattr(location, "longitude"):
        lat, lon = location.latitude, location.longitude
    elif isinstance(location, dict):
        lat = location.get("latitude") or location.get("lat")
        lon = location.get("longitude") or location.get("lng") or location.get("lon")

    if lat is not None and lon is not None:
        try:
            # PostGIS ST_MakePoint explicitly requires (Longitude, Latitude) -> (X, Y)
            return func.ST_SetSRID(
                func.ST_MakePoint(float(lon), float(lat)), 4326
            ).cast(Geography)
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Failed to cast location coordinates (lat={lat}, lon={lon}): {e}"
            )
            return None

    return location


def calculate_match_score(distance: float) -> float:
    """
    The system's single source of truth scoring mechanism (Sigmoid).
    Uses a gentler curve (8.0 multiplier) to prevent "cliff edge" drop-offs.
    """
    try:
        return max(
            0.0,
            min(
                100.0,
                round((1.0 / (1.0 + math.exp(8.0 * (distance - 0.60)))) * 100.0, 2),
            ),
        )
    except Exception:
        return 0.0


def _extract_json_array(raw_text: str) -> list[Any]:
    """Robustly extracts a JSON array from LLM responses using standard parsing and regex fallback."""
    cleaned_text = (
        raw_text.strip()
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )

    # Attempt 1: Standard JSON parse
    try:
        data = json.loads(cleaned_text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return next((v for v in data.values() if isinstance(v, list)), [])
    except json.JSONDecodeError:
        pass

    # Attempt 2: Regex search for embedded JSON array
    match = re.search(r"\[\s*.*?\s*\]", raw_text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    return []


def _search_workers(
    db: Session,
    query_vector: list[float],
    customer_location: Any,
    radius_meters: int,
    job_category: Optional[str] = None, # Kept for signature compatibility, but strict ILIKE filtering is removed
) -> list[tuple[model.WorkerProfile, model.User, model.WorkerSkill, float]]:
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
        )
    )

    # Strict ILIKE category filtering removed here to make Client & Worker flows symmetrical. 
    # We now trust the vector search + LLM Reranker to handle the job_category semantically.

    if spatial_point is not None:
        stmt = stmt.where(
            func.ST_DWithin(model.WorkerProfile.location, spatial_point, radius_meters)
        )

    stmt = stmt.order_by(distance_expr.asc())
    return db.execute(stmt).all()


def _deduplicate_by_user(
    search_results: list[
        tuple[model.WorkerProfile, model.User, model.WorkerSkill, float]
    ],
) -> list[tuple[model.WorkerProfile, model.User, model.WorkerSkill, float]]:
    seen_user_ids: set[int] = set()
    deduped: list[tuple[model.WorkerProfile, model.User, model.WorkerSkill, float]] = []

    for worker, user, skill, distance in search_results:
        user_key = (
            getattr(user, "id", None) or getattr(worker, "user_id", None) or worker.id
        )

        if user_key in seen_user_ids:
            continue

        seen_user_ids.add(user_key)
        deduped.append((worker, user, skill, distance))

    return deduped


def _build_candidate_summary(match: MatchDetail) -> dict:
    worker = match["worker_profile"]
    return {
        "worker_id": worker.id,
        "vector_rank": match["rank"],
        "vector_score": match["score"],
        "job_category": getattr(worker, "job_category", None),
        "category_tag": getattr(worker, "category_tag", None),
        "matched_skill_title": match.get("matched_skill_title"),
        "matched_skill_description": match.get("matched_skill_description"),
        "profile_summary": getattr(worker, "job_description", ""),
    }


def _llm_rerank_matches(
    job_description: str,
    job_category: Optional[str],
    rich_matches: list[MatchDetail],
) -> list[MatchDetail]:
    if not rich_matches:
        return rich_matches

    candidates = rich_matches[:MAX_CANDIDATES_FOR_RERANK]
    candidate_payload = [_build_candidate_summary(m) for m in candidates]

    # Softer prompt focused on ranking rather than aggressive deletion
    prompt = (
        "You are a helpful assistant sorting tradespeople for a customer's job.\n\n"
        f"Job category: {job_category or 'unknown'}\n"
        f"Job description:\n{job_description}\n\n"
        f"Candidates (JSON):\n{json.dumps(candidate_payload)}\n\n"
        "Rank these candidates from best fit to worst fit based on how well their skills match the job description. "
        "Omit candidates ONLY if their trade is completely irrelevant to the job.\n\n"
        "Return ONLY a JSON array of worker_id integers, ordered best fit first."
    )

    try:
        client = _get_nvidia_client()
        response = client.chat.completions.create(
            model=RERANK_MODEL,
            max_tokens=1024,
            temperature=0.0, # STABILIZES THE OUTPUT - No more mood swings
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.choices[0].message.content or ""
        parsed_ids = _extract_json_array(raw_text)

        ordered_ids = [
            int(x) for x in parsed_ids if isinstance(x, (int, str)) and str(x).isdigit()
        ]

    except Exception as e:
        logger.error(f"LLM reranker exception, using vector fallback: {e}")
        return candidates

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

    return reranked


def _build_job_candidate_summary(
    job: model.Job, skill: model.WorkerSkill, score: float, rank: int
) -> dict:
    return {
        "job_id": job.id,
        "vector_rank": rank,
        "vector_score": score,
        "job_title": getattr(job, "title", None) or "General Task",
        "job_description": job.description,
        "categories": getattr(job, "categories", None)
        or getattr(job, "job_category", None),
        "matched_worker_skill_title": skill.title,
        "matched_worker_skill_description": skill.description,
    }


def _llm_rerank_jobs_for_worker(
    worker_profile: Optional[model.WorkerProfile],
    worker_skills: list[model.WorkerSkill],
    candidate_jobs: list[dict],
) -> list[dict]:
    if not candidate_jobs:
        return candidate_jobs

    candidates = candidate_jobs[:MAX_CANDIDATES_FOR_RERANK]

    worker_summary = {
        "job_category": getattr(worker_profile, "job_category", "Unknown"),
        "category_tag": getattr(worker_profile, "category_tag", "Unknown"),
        "profile_summary": getattr(worker_profile, "job_description", ""),
        "active_skills": [
            {"title": s.title, "description": s.description}
            for s in worker_skills
            if s.is_active
        ],
    }

    candidate_payload = [
        _build_job_candidate_summary(m["job"], m["skill"], m["score"], m["rank"])
        for m in candidates
    ]

    # Softer prompt focused on ranking rather than aggressive deletion
    prompt = (
        "You are a helpful assistant matching a tradesperson to available customer jobs.\n\n"
        f"Worker Capabilities:\n{json.dumps(worker_summary, indent=2)}\n\n"
        f"Candidate Jobs:\n{json.dumps(candidate_payload, indent=2)}\n\n"
        "Rank these jobs from best fit to worst fit based on the worker's capabilities. "
        "Omit jobs ONLY if the worker is completely unqualified to perform them.\n\n"
        "Return ONLY a JSON array of the job_id integers, ordered best fit first."
    )

    try:
        client = _get_nvidia_client()
        response = client.chat.completions.create(
            model=RERANK_MODEL,
            max_tokens=1024,
            temperature=0.0, # STABILIZES THE OUTPUT - No more mood swings
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.choices[0].message.content or ""
        parsed_ids = _extract_json_array(raw_text)

        ordered_ids = [
            int(x) for x in parsed_ids if isinstance(x, (int, str)) and str(x).isdigit()
        ]

    except Exception as e:
        logger.error(f"LLM worker reranker exception, using vector fallback: {e}")
        return candidates

    by_job_id = {int(m["job"].id): m for m in candidates}
    reranked: list[dict] = []
    seen_ids: set[int] = set()

    for new_rank, job_id in enumerate(ordered_ids, start=1):
        match = by_job_id.get(job_id)
        if match is None or job_id in seen_ids:
            continue
        match["rank"] = new_rank
        reranked.append(match)
        seen_ids.add(job_id)

    return reranked


def create_matches_for_job(
    db: Session,
    job_id: int,
    query_vector: list[float],
    customer_location: Any,
    radius_meters: int = 60_000, # Matched default fallback with worker function
    job_description: str = "",
    job_category: Optional[str] = None,
) -> MatchingResult:
    """Creates/Updates matches for a customer job without destroying user interaction state."""
    search_results = _search_workers(
        db, query_vector, customer_location, radius_meters, job_category
    )
    search_results = _deduplicate_by_user(search_results)

    rich_matches: list[MatchDetail] = []
    vector_rank = 1

    for worker, user, skill, distance in search_results:
        dist_val = float(distance)
        score = calculate_match_score(dist_val)
        if score > SCORE_THRESHOLD:
            rich_matches.append(
                {
                    "worker_profile": worker,
                    "user": user,
                    "score": score,
                    "rank": vector_rank,
                    "distance": dist_val,
                    "worker_chat_id": getattr(worker, "worker_chat_id", None),
                    "matched_skill_id": skill.id,
                    "matched_skill_title": skill.title,
                    "matched_skill_description": skill.description,
                }
            )
            vector_rank += 1

    rich_matches = _llm_rerank_matches(job_description, job_category, rich_matches)

    # Fetch existing matches to preserve user response state
    existing_matches = {
        m.worker_id: m
        for m in db.query(model.JobWorkerMatch)
        .filter(model.JobWorkerMatch.job_id == job_id)
        .all()
    }

    matched_worker_ids = set()
    notifiable_worker_chat_ids = []

    for match in rich_matches:
        worker = match["worker_profile"]
        matched_worker_ids.add(worker.id)

        if worker.id in existing_matches:
            # Update existing record, preserving user flags
            match_row = existing_matches[worker.id]
            match_row.matched_skill_id = match.get("matched_skill_id")
            match_row.match_score = match["score"]
            match_row.match_rank = match["rank"]
            match_row.semantic_distance = match["distance"]
            match_row.is_active = True
        else:
            # Create new record
            match_row = model.JobWorkerMatch(
                job_id=job_id,
                worker_id=worker.id,
                matched_skill_id=match.get("matched_skill_id"),
                match_score=match["score"],
                match_rank=match["rank"],
                semantic_distance=match["distance"],
                is_active=True,
                is_interested=False,
                is_selected=False,
                is_rejected=False,
            )
            db.add(match_row)

        if match.get("worker_chat_id"):
            notifiable_worker_chat_ids.append(match["worker_chat_id"])

    # Deactivate matches that are no longer valid, keeping records for historical integrity
    for w_id, old_match in existing_matches.items():
        if w_id not in matched_worker_ids:
            old_match.is_active = False

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
    worker_profile = (
        db.query(model.WorkerProfile)
        .filter(model.WorkerProfile.id == worker_id)
        .first()
    )
    worker_skills = (
        db.query(model.WorkerSkill)
        .filter(
            model.WorkerSkill.worker_id == worker_id,
            model.WorkerSkill.is_active.is_(True),
        )
        .all()
    )

    if not worker_skills:
        return {"matched_jobs": [], "count": 0}

    distance_expr = model.Job.description_vector.cosine_distance(
        model.WorkerSkill.embedding
    )
    spatial_point = _ensure_geography(
        worker_location or getattr(worker_profile, "location", None)
    )

    stmt = (
        select(
            model.Job,
            model.WorkerSkill,
            distance_expr.label("distance"),
        )
        .select_from(model.Job)
        .join(
            model.WorkerSkill,
            (model.WorkerSkill.worker_id == worker_id)
            & (model.WorkerSkill.is_active.is_(True)),
        )
        .where(
            model.WorkerSkill.embedding.isnot(None),
            model.Job.description_vector.isnot(None),
            model.Job.status.ilike("pending"),
        )
    )

    if spatial_point is not None:
        stmt = stmt.where(
            func.ST_DWithin(model.Job.location, spatial_point, radius_meters)
        )

    stmt = stmt.order_by(distance_expr.asc())
    search_results = db.execute(stmt).all()

    seen_job_ids: set[int] = set()
    candidate_jobs: list[dict] = []
    vector_rank = 1

    for job, skill, distance in search_results:
        if job.id in seen_job_ids:
            continue
        seen_job_ids.add(job.id)

        dist_val = float(distance)
        score = calculate_match_score(dist_val)
        if score > SCORE_THRESHOLD:
            candidate_jobs.append(
                {
                    "job": job,
                    "skill": skill,
                    "distance": dist_val,
                    "score": score,
                    "rank": vector_rank,
                }
            )
            vector_rank += 1

    candidate_jobs = _llm_rerank_jobs_for_worker(
        worker_profile, worker_skills, candidate_jobs
    )

    existing_matches = {
        m.job_id: m
        for m in db.query(model.JobWorkerMatch)
        .filter(model.JobWorkerMatch.worker_id == worker_id)
        .all()
    }

    matched_job_ids = set()
    matched_jobs_payload: list[MatchedJobDetail] = []

    for item in candidate_jobs:
        job = item["job"]
        skill = item["skill"]
        score = item["score"]
        rank = item["rank"]
        distance = item["distance"]

        matched_job_ids.add(job.id)

        if job.id in existing_matches:
            match_row = existing_matches[job.id]
            match_row.matched_skill_id = skill.id
            match_row.match_score = score
            match_row.match_rank = rank
            match_row.semantic_distance = distance
            match_row.is_active = True
        else:
            match_row = model.JobWorkerMatch(
                job_id=job.id,
                worker_id=worker_id,
                matched_skill_id=skill.id,
                match_score=score,
                match_rank=rank,
                semantic_distance=distance,
                is_active=True,
                is_interested=False,
                is_selected=False,
                is_rejected=False,
            )
            db.add(match_row)

        matched_jobs_payload.append(
            {
                "booking_chat_id": getattr(job, "booking_chat_id", None),
                "title": getattr(job, "title", "General Task"),
                "description": job.description,
                "score": score,
                "rank": rank,
                "matched_skill_title": skill.title,
            }
        )

    # Deactivate matches that no longer meet the threshold
    for j_id, old_match in existing_matches.items():
        if j_id not in matched_job_ids:
            old_match.is_active = False

    db.flush()

    return {
        "matched_jobs": matched_jobs_payload,
        "count": len(matched_jobs_payload),
    }