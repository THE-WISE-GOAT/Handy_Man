from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, func, cast, or_
from src.database.database import get_db
from src.core.oauth2 import get_current_user
from src.core import model
from geoalchemy2 import Geometry

router = APIRouter(prefix="/workers", tags=["Workers"])


class WorkerLocationsIn(BaseModel):
    worker_chat_ids: list[int]


@router.post("/locations", summary="Fetch exact coordinates for a batch of workers")
def get_worker_locations(
    payload: WorkerLocationsIn,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    if not payload.worker_chat_ids:
        return {"status": "success", "locations": []}

    stmt = select(
        model.WorkerProfile.worker_chat_id,
        func.ST_Y(cast(model.WorkerProfile.location, Geometry)).label("latitude"),
        func.ST_X(cast(model.WorkerProfile.location, Geometry)).label("longitude"),
    ).where(
        model.WorkerProfile.worker_chat_id.in_(payload.worker_chat_ids),
        model.WorkerProfile.location.isnot(None),
    )

    results = db.execute(stmt).all()

    locations = [
        {
            "worker_chat_id": row.worker_chat_id,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "is_interested": False,
        }
        for row in results
    ]

    return {"status": "success", "locations": locations}


@router.get(
    "/jobs/{job_id}/bids",
    summary="Fetch all bids from JobWorkerMatch for a specific job",
)
def get_worker_job_bids(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    job = db.execute(
        select(model.Job).where(
            or_(
                model.Job.id == job_id,
                model.Job.booking_chat_id == str(job_id),
            )
        )
    ).scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found."
        )

    actual_job_id = job.id

    stmt = (
        select(model.JobWorkerMatch, model.WorkerProfile, model.User)
        .join(model.WorkerProfile, model.JobWorkerMatch.worker_id == model.WorkerProfile.id)
        .join(model.User, model.WorkerProfile.user_id == model.User.id)
        .where(
            model.JobWorkerMatch.job_id == actual_job_id,
            model.JobWorkerMatch.is_active == True,
            model.JobWorkerMatch.bid_amount.isnot(None),
        )
    )

    results = db.execute(stmt).all()

    formatted_bids = [
        {
            "id": match.id,
            "worker_id": match.worker_id,
            "worker_chat_id": worker.worker_chat_id,
            "worker_name": f"{user.firstName or ''} {user.lastName or ''}".strip() or user.username,
            "amount": float(match.bid_amount),
            "proposal_text": match.bid_message,
            "is_interested": match.is_interested,
            "status": (
                "Accepted"
                if match.is_selected
                else ("Rejected" if match.is_rejected else "Pending")
            ),
            "created_at": match.created_at,
        }
        for match, worker, user in results
    ]

    return {"status": "success", "bids": formatted_bids}
