import math
from typing import List

from sqlalchemy import select, func, delete
from sqlalchemy.orm import Session

from src.database import model


MATCH_SCORE_THRESHOLD = 55.0
DEFAULT_SEARCH_RADIUS_METERS = 10000


def calculate_match_score(distance: float) -> float:
    """
    Converts pgvector cosine distance into a human-readable percentage.
    """

    return max(
        0.0,
        min(
            100.0,
            round(
                (
                    1.0
                    / (
                        1.0
                        + math.exp(
                            15.0 * (distance - 0.87)
                        )
                    )
                )
                * 100.0,
                2,
            ),
        ),
    )


def _search_workers(
    db: Session,
    query_vector: List[float],
    customer_location,
    radius_meters: float = DEFAULT_SEARCH_RADIUS_METERS,
):
    """
    Returns all eligible workers ordered by semantic similarity.
    """

    distance_expr = model.WorkerProfile.description_vector.cosine_distance(
        query_vector
    )

    stmt = (
        select(
            model.WorkerProfile,
            model.User,
            distance_expr.label("distance"),
        )
        .join(
            model.User,
            model.User.id == model.WorkerProfile.user_id,
        )
        .where(
            model.WorkerProfile.is_complete.is_(True),
            model.WorkerProfile.description_vector.is_not(None),
            model.WorkerProfile.location.is_not(None),
            func.ST_DWithin(
                model.WorkerProfile.location,
                customer_location,
                radius_meters,
            ),
        )
        .order_by(distance_expr.asc())
    )

    return db.execute(stmt).all()


def rank_matches(matches: list[dict]) -> list[dict]:
    """
    Highest score receives rank 1.
    """

    matches.sort(
        key=lambda m: m["match_score"],
        reverse=True,
    )

    for rank, match in enumerate(matches, start=1):
        match["rank"] = rank

    return matches


def persist_job_matches(
    db: Session,
    job: model.Job,
    ranked_matches: list[dict],
):
    """
    Replaces the existing matches for this job with the newest ones.
    """

    db.execute(
        delete(model.JobWorkerMatch).where(
            model.JobWorkerMatch.job_id == job.id
        )
    )

    persisted_matches = []

    for match in ranked_matches:

        db_match = model.JobWorkerMatch(
            job_id=job.id,
            worker_id=match["worker"].id,
            match_score=match["match_score"],
            match_rank=match["rank"],
            semantic_distance=match["distance"],
            is_active=True,
        )

        db.add(db_match)

        persisted_matches.append(
            {
                **match,
                "db_match": db_match,
            }
        )

    db.commit()

    return persisted_matches


def create_matches_for_job(
    db: Session,
    job: model.Job,
):
    """
    Customer-side matching engine.

    Flow

        Search workers
            ↓
        Calculate scores
            ↓
        Remove weak matches
            ↓
        Rank
            ↓
        Persist
            ↓
        Return persisted matches
    """

    raw_matches = _search_workers(
        db=db,
        query_vector=job.description_vector,
        customer_location=job.location,
    )

    matches = []

    for worker, user, distance in raw_matches:

        score = calculate_match_score(distance)

        if score < MATCH_SCORE_THRESHOLD:
            continue

        matches.append(
            {
                "worker": worker,
                "user": user,
                "distance": distance,
                "match_score": score,
            }
        )

    ranked_matches = rank_matches(matches)

    persisted_matches = persist_job_matches(
        db=db,
        job=job,
        ranked_matches=ranked_matches,
    )

    return persisted_matches


def get_matches_for_job(
    db: Session,
    job_id: int,
):
    """
    Returns persisted matches for a job ordered by rank.
    This will replace the current implementation of /find-help.
    """

    stmt = (
        select(
            model.JobWorkerMatch,
            model.WorkerProfile,
            model.User,
        )
        .join(
            model.WorkerProfile,
            model.WorkerProfile.id == model.JobWorkerMatch.worker_id,
        )
        .join(
            model.User,
            model.User.id == model.WorkerProfile.user_id,
        )
        .where(
            model.JobWorkerMatch.job_id == job_id,
            model.JobWorkerMatch.is_active.is_(True),
        )
        .order_by(model.JobWorkerMatch.match_rank.asc())
    )

    return db.execute(stmt).all()