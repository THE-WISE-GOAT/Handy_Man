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
    Executes vector search across all active WorkerExpertise vectors.
    Collapses multiple expertise vectors per worker down to the SINGLE best matching
    (lowest cosine distance) expertise vector using a SQL subquery.
    """
    distance_expr = model.WorkerExpertise.embedding.cosine_distance(query_vector)

    # 1. Subquery: find the minimum distance among active expertise vectors per worker
    best_expertise_subq = (
        select(
            model.WorkerProfile.id.label("worker_id"),
            func.min(distance_expr).label("best_distance")
        )
        .join(model.WorkerExpertise, model.WorkerExpertise.worker_id == model.WorkerProfile.id)
        .where(
            model.WorkerExpertise.embedding.isnot(None),
            model.WorkerExpertise.is_active.is_(True),
            model.WorkerProfile.location.isnot(None),
            model.WorkerProfile.is_complete.is_(True),
            model.WorkerProfile.is_rejected.is_(False),
            func.ST_DWithin(model.WorkerProfile.location, customer_location, radius_meters),
        )
        .group_by(model.WorkerProfile.id)
        .subquery()
    )

    # 2. Main query: join candidates and order globally by their best distance
    stmt = (
        select(
            model.WorkerProfile,
            model.User,
            best_expertise_subq.c.best_distance.label("distance")
        )
        .join(model.WorkerProfile, model.WorkerProfile.id == best_expertise_subq.c.worker_id)
        .join(model.User, model.User.id == model.WorkerProfile.user_id)
        .order_by(best_expertise_subq.c.best_distance.asc())
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
    Core Entry Point: Purges stale matches, processes candidates whose BEST expertise 
    crosses the threshold, ranks them, and flushes changes to the session.
    """
    # 1. Clear historical stale match rows for this job
    db.query(model.JobWorkerMatch).filter(
        model.JobWorkerMatch.job_id == job_id
    ).delete(synchronize_session=False)

    # 2. Extract potential candidate profiles (ordered by best expertise distance)
    search_results = _search_workers(db, query_vector, customer_location, radius_meters)
    
    new_match_records = []
    rich_matches: list[MatchDetail] = []
    notifiable_worker_chat_ids = []
    current_rank = 1

    for worker, user, distance in search_results:
        score = calculate_match_score(float(distance))
            
        if score > SCORE_THRESHOLD:
            match_row = model.JobWorkerMatch(
                job_id=job_id,
                worker_id=worker.id,
                match_score=score,
                match_rank=current_rank,
                semantic_distance=float(distance),
                is_active=True,
                is_interested=False,
                is_selected=False,
                is_rejected=False
            )
            new_match_records.append(match_row)
            
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
    Reverse Job Matching Entry Point: Evaluates distance between all active pending jobs
    and ALL active expertise vectors for this specific worker, selecting the best match per job.
    """
    logger.info(f"Running reverse multi-vector matching pipeline for worker_id: {worker_id}")

    # 1. Clear out historical stale match rows for this worker
    db.query(model.JobWorkerMatch).filter(
        model.JobWorkerMatch.worker_id == worker_id
    ).delete(synchronize_session=False)

    # 2. Compute cosine distance between open jobs and worker's expertise vectors
    distance_expr = model.Job.description_vector.cosine_distance(model.WorkerExpertise.embedding)

    # Subquery: calculate best distance for each pending job across ALL of this worker's expertise records
    best_job_match_subq = (
        select(
            model.Job.id.label("job_id"),
            func.min(distance_expr).label("best_distance")
        )
        .join(model.WorkerExpertise, model.WorkerExpertise.worker_id == worker_id)
        .where(
            model.Job.description_vector.isnot(None),
            model.Job.location.isnot(None),
            model.Job.status == "pending",
            model.WorkerExpertise.embedding.isnot(None),
            model.WorkerExpertise.is_active.is_(True),
            func.ST_DWithin(model.Job.location, worker_location, radius_meters),
        )
        .group_by(model.Job.id)
        .subquery()
    )

    stmt = (
        select(model.Job, best_job_match_subq.c.best_distance.label("distance"))
        .join(model.Job, model.Job.id == best_job_match_subq.c.job_id)
        .order_by(best_job_match_subq.c.best_distance.asc())
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