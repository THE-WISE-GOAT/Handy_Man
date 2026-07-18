import math
import logging
from typing import TypedDict, Any
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from src.core import model

logger = logging.getLogger(__name__)

SCORE_THRESHOLD = 75.5

class MatchDetail(TypedDict):
    worker_profile: model.WorkerProfile
    user: model.User
    score: float
    rank: int
    worker_chat_id: int

class MatchingResult(TypedDict):
    matches: list[MatchDetail]
    worker_chat_ids: list[int]
    count: int

class MatchedJobDetail(TypedDict):
    booking_chat_id: int
    title: str
    description: str
    score: float
    rank: int

class WorkerMatchingResult(TypedDict):
    matched_jobs: list[MatchedJobDetail]
    count: int


def _search_workers(
    db: Session,
    query_vector: list[float],
    customer_location,
    radius_meters: int,
) -> list[tuple[model.WorkerProfile, model.User, float]]:
    """
    Executes a limitless semantic vector search query across eligible worker pools.
    Relies entirely on the semantic vector as the absolute source of truth.
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
        .order_by(distance_expr)
    )

    return db.execute(stmt).all()


def calculate_match_score(distance: float) -> float:
    """The system's single source of truth scoring mechanism (Sigmoid)."""
    try:
        return max(0.0, min(100.0, round((1.0 / (1.0 + math.exp(25.0 * (distance - 0.90)))) * 100.0, 2)))
    except Exception:
        return 0.0


def create_matches_for_job(
    db: Session,
    job_id: int,
    query_vector: list[float],
    customer_location,
    radius_meters: int
) -> MatchingResult:
    """
    Core Entry Point: Purges stale matches, processes every candidate crossing the 
    threshold, ranks them according to DB distance order, and flushes changes to the session.
    """
    # 1. Clear out historical stale match rows for this specific job context
    db.query(model.JobWorkerMatch).filter(
        model.JobWorkerMatch.job_id == job_id
    ).delete(synchronize_session=False)

    # 2. Extract every potential candidate profile within radius (ordered by database distance)
    search_results = _search_workers(db, query_vector, customer_location, radius_meters)
    
    new_match_records = []
    rich_matches: list[MatchDetail] = []
    notifiable_worker_chat_ids = []
    current_rank = 1

# 3. Process all records matching the threshold without an artificial cap
    for worker, user, distance in search_results:
        score = calculate_match_score(float(distance))
            
        if score > SCORE_THRESHOLD:
            # Core relationship mapping table execution
            match_row = model.JobWorkerMatch(
                job_id=job_id,
                worker_id=worker.id,
                match_score=score,
                match_rank=current_rank,
                semantic_distance=float(distance),  # ─── ADD THIS LINE ───
                is_active=True,
                is_interested=False,
                is_selected=False,
                is_rejected=False
            )
            new_match_records.append(match_row)
            
            # Populate rich structural payload for downstream router operations
            rich_matches.append({
                "worker_profile": worker,
                "user": user,
                "score": score,
                "rank": current_rank,
                "worker_chat_id": worker.worker_chat_id
            })
            notifiable_worker_chat_ids.append(worker.worker_chat_id)
            current_rank += 1

    if new_match_records:
        db.add_all(new_match_records)
        db.flush()  # Stages matches so primary keys/states are accessible without committing
        
    return {
        "matches": rich_matches,
        "worker_chat_ids": notifiable_worker_chat_ids,
        "count": len(rich_matches)
    }


def create_matches_for_worker(
    db: Session,
    worker_id: int,
    query_vector: list[float],
    worker_location,
    radius_meters: int
) -> WorkerMatchingResult:
    """
    Reverse Job Matching Entry Point: Triggered upon successful worker onboarding completion.
    Purges stale historical matches for this worker, scans for compatible open/active jobs
    in a 'pending' state within the marketplace radius, ranks them, and persists matches.
    """
    logger.info(f"Running reverse matching pipeline for worker_id: {worker_id}")

    # 1. Clear out historical stale match rows for this specific worker context
    db.query(model.JobWorkerMatch).filter(
        model.JobWorkerMatch.worker_id == worker_id
    ).delete(synchronize_session=False)

    # 2. Execute semantic vector distance calculations against active, pending client jobs
    distance_expr = model.Job.description_vector.cosine_distance(query_vector)

    stmt = (
        select(model.Job, distance_expr.label("distance"))
        .where(
            model.Job.description_vector.isnot(None),
            model.Job.location.isnot(None),
            model.Job.status == "pending",  # Enforce matching ONLY open, unresolved opportunities
            func.ST_DWithin(model.Job.location, worker_location, radius_meters),
        )
        .order_by(distance_expr)
    )

    search_results = db.execute(stmt).all()

    new_match_records = []
    matched_jobs_payload: list[MatchedJobDetail] = []
    current_rank = 1

# 3. Filter candidates through the standard sigmoid score boundary
    for job, distance in search_results:
        score = calculate_match_score(float(distance))

        if score > SCORE_THRESHOLD:
            match_row = model.JobWorkerMatch(
                job_id=job.id,
                worker_id=worker_id,
                match_score=score,
                match_rank=current_rank,
                semantic_distance=float(distance),  # ─── ADD THIS LINE ───
                is_active=True,
                is_interested=False,
                is_selected=False,
                is_rejected=False
            )
            new_match_records.append(match_row)

            # Construct structured output required by chat_worker onboarding router
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
        db.flush()  # Stages matches so primary keys are available downstream before transaction commit

    return {
        "matched_jobs": matched_jobs_payload,
        "count": len(matched_jobs_payload)
    }