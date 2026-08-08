# routers/job_router.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session
from src.core import model, schema, job_manager, matching_manager
from src.database.database import get_db
from src.core.oauth2 import get_current_user
from src.ai.worker_chat_analyser_nvidia import get_worker_description_embedding
import logging
import httpx

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)

DEFAULT_SEARCH_RADIUS_METERS = 60_000


async def _get_address_from_coords(lat: float, lng: float) -> str:
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"lat": lat, "lon": lng, "format": "json", "addressdetails": 1}
    headers = {
        "User-Agent": "WorkerVerificationApp/1.0 (contact: admin@yourdomain.com)"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, params=params, headers=headers, timeout=8.0
            )
            if response.status_code == 200:
                data = response.json()
                if "display_name" in data:
                    return data["display_name"]
    except Exception as e:
        logger.error(f"[Geocode Exception] {e}")
    return f"Location ({lat}, {lng})"


async def _broadcast_notifications(worker_chat_ids: list[int], job_payload: dict):
    from src.core.manager import manager

    for worker_chat_id in worker_chat_ids:
        try:
            await manager.send_worker_notification(worker_chat_id, job_payload)
        except Exception as ws_err:
            logger.warning(f"Failed live alert broadcast to worker {worker_chat_id}: {ws_err}")


async def _broadcast_customer_bid(booking_chat_id: int, bid_payload: dict):
    """Send a SYSTEM_BID notification to the customer's WebSocket connection."""
    from src.core.manager import manager
    try:
        await manager.send_customer_notification(booking_chat_id, bid_payload)
    except Exception as ws_err:
        logger.warning(f"Failed SYSTEM_BID broadcast to booking {booking_chat_id}: {ws_err}")


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a job directly without AI chat")
async def create_job_direct_endpoint(
    payload: schema.CreateJobIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    lng = payload.location.longitude
    lat = payload.location.latitude
    wkt_point = f"POINT({lng} {lat})"

    job_desc = payload.description.strip()
    if not job_desc:
        job_desc = f"{payload.title}: {payload.contact_name or ''}".strip()
    if not job_desc:
        raise HTTPException(status_code=400, detail="Job description is required.")

    try:
        embedding_vector = await get_worker_description_embedding(job_desc)
    except Exception as exc:
        logger.error(f"Embedding error: {exc}")
        raise HTTPException(status_code=502, detail="Failed to generate job embedding.")

    address_text = await _get_address_from_coords(lat, lng)

    categories = []
    if payload.category:
        categories = [{"category": payload.category, "tags": [], "is_custom_category": False}]

    job_fields = {
        "title": payload.title,
        "description": job_desc,
        "status": payload.status,
        "is_job_request": True,
        "categories": categories,
        "contact_name": payload.contact_name,
        "contact_phone": payload.contact_phone,
        "mode": payload.mode,
        "scheduled_date": payload.scheduled_date,
        "attachments": payload.attachments,
        "latitude": lat,
        "longitude": lng,
        "location": wkt_point,
        "description_vector": embedding_vector,
        "address_text": address_text,
    }

    try:
        job_data = job_manager.create_job_direct(db, current_user.id, job_fields)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Job creation failed: {e}")
        raise HTTPException(status_code=500, detail="Database update failed.")

    try:
        matching_result = matching_manager.create_matches_for_job(
            db=db,
            job_id=job_data.id,
            query_vector=embedding_vector,
            customer_location=wkt_point,
            radius_meters=DEFAULT_SEARCH_RADIUS_METERS,
        )
        db.commit()
    except Exception as engine_err:
        db.rollback()
        logger.error(f"Matching Engine failed: {engine_err}")
        raise HTTPException(status_code=500, detail="Failed to compile marketplace matches.")

    job_payload = {
        "booking_chat_id": None,
        "title": payload.title,
        "description": job_desc,
    }

    worker_chat_ids = matching_result.get("worker_chat_ids", [])
    if worker_chat_ids:
        background_tasks.add_task(_broadcast_notifications, worker_chat_ids, job_payload)

    return {
        "status": "success",
        "message": f"Job created. Established {matching_result.get('count', 0)} matches successfully.",
        "job_id": job_data.id,
    }


@router.get("/status/{status_val}")
def get_jobs_by_status_endpoint(
    status_val: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    results = job_manager.get_jobs_by_status(
        db, current_user.id, status_val, skip, limit
    )

    formatted_tasks = [
        {
            "id": row.id,
            "booking_chat_id": row.booking_chat_id,
            "title": row.title,
            "description": row.description,
            "status": row.status,
            "contact_name": row.contact_name,
            "contact_phone": row.contact_phone,
            "attachments": row.attachments,
            "address_text": row.address_text,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "updated_at": row.updated_at,
            "matched_count": row.matched_count or 0,
            "interested_count": row.interested_count or 0,
        }
        for row in results
    ]

    return {"status": "success", "tasks": formatted_tasks}


@router.delete("/{job_id}", summary="Delete a specific job")
def delete_job_endpoint(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    success = job_manager.delete_job(db, job_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or unauthorized")

    return {"status": "success", "message": "Job deleted successfully"}


interest_subquery = (
    select(
        model.JobWorkerMatch.job_id,
        func.count(model.JobWorkerMatch.id).label("interested_count"),
    )
    .where(
        model.JobWorkerMatch.is_active == True,
        model.JobWorkerMatch.is_interested == True,
    )
    .group_by(model.JobWorkerMatch.job_id)
    .subquery()
)


@router.get("/for-worker", summary="Fetch all active matched jobs for the authenticated worker")
def get_worker_matched_jobs(
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user)
):
    try:
        worker_profiles = db.execute(
            select(model.WorkerProfile).where(
                model.WorkerProfile.user_id == current_user.id
            )
        ).scalars().all()

        if not worker_profiles:
            return {"status": "success", "jobs": []}

        worker_profile_ids = [profile.id for profile in worker_profiles]

        stmt = (
            select(model.JobWorkerMatch, model.Job, func.coalesce(interest_subquery.c.interested_count, 0))
            .join(model.Job, model.JobWorkerMatch.job_id == model.Job.id)
            .outerjoin(interest_subquery, model.Job.id == interest_subquery.c.job_id)
            .where(
                model.JobWorkerMatch.worker_id.in_(worker_profile_ids),
                model.JobWorkerMatch.is_active == True,
                model.JobWorkerMatch.is_rejected == False,
            )
            .order_by(model.JobWorkerMatch.created_at.desc())
        )

        results = db.execute(stmt).all()

        jobs = [
            {
                "job_id": job.id,
                "booking_chat_id": job.booking_chat_id,
                "title": job.title,
                "description": job.description,
                "status": job.status,
                "worker_id": job.worker_id,
                "location": job.address_text,
                "match_score": match.match_score,
                "match_rank": match.match_rank,
                "created_at": match.created_at,
                "is_interested": match.is_interested,
                "interested_count": int(interest_count),
            }
            for match, job, interest_count in results
        ]

        return {"status": "success", "jobs": jobs}
    except Exception as exc:
        logger.error("Error in get_worker_matched_jobs: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch matched jobs.")


@router.post("/{job_id}/interest", summary="Worker expresses interest in a job")
def express_interest_in_job(
    job_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    worker_profiles = db.execute(
        select(model.WorkerProfile).where(
            model.WorkerProfile.user_id == current_user.id
        )
    ).scalars().all()

    if not worker_profiles:
        raise HTTPException(status_code=404, detail="Worker profile not found")

    worker_profile_ids = [profile.id for profile in worker_profiles]

    match = db.execute(
        select(model.JobWorkerMatch).where(
            model.JobWorkerMatch.job_id == job_id,
            model.JobWorkerMatch.worker_id.in_(worker_profile_ids),
            model.JobWorkerMatch.is_active == True,
        )
    ).scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=404, detail="No active match found for this job")

    requested_interest = payload.get("interested", True)
    match.is_interested = bool(requested_interest)
    db.commit()
    db.refresh(match)

    interested_count = db.execute(
        select(func.count(model.JobWorkerMatch.id)).where(
            model.JobWorkerMatch.job_id == job_id,
            model.JobWorkerMatch.is_active == True,
            model.JobWorkerMatch.is_interested == True,
        )
    ).scalar_one()

    return {
        "status": "success",
        "job_id": job_id,
        "is_interested": match.is_interested,
        "interested_count": int(interested_count or 0),
    }


@router.post("/{job_id}/bid", summary="Worker places a bid on a job")
async def place_bid_on_job(
    job_id: int,
    payload: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    """Record (or update) the worker's bid amount and proposal text."""
    worker_profiles = db.execute(
        select(model.WorkerProfile).where(
            model.WorkerProfile.user_id == current_user.id
        )
    ).scalars().all()

    if not worker_profiles:
        raise HTTPException(status_code=404, detail="Worker profile not found")

    worker_profile_ids = [profile.id for profile in worker_profiles]

    match = db.execute(
        select(model.JobWorkerMatch).where(
            model.JobWorkerMatch.job_id == job_id,
            model.JobWorkerMatch.worker_id.in_(worker_profile_ids),
            model.JobWorkerMatch.is_active == True,
        )
    ).scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=404, detail="No active match found for this job")

    matched_profile = next(
        (profile for profile in worker_profiles if profile.id == match.worker_id),
        worker_profiles[0],
    )

    bid_amount = payload.get("bid_amount")
    bid_message = payload.get("bid_message", "")

    if bid_amount is not None:
        match.bid_amount = float(bid_amount)
    if bid_message:
        match.bid_message = bid_message

    db.commit()
    db.refresh(match)

    job = db.execute(
        select(model.Job).where(model.Job.id == job_id)
    ).scalar_one_or_none()

    if job and job.booking_chat_id:
        worker_name = f"{getattr(current_user, 'firstName', None) or ''} {getattr(current_user, 'lastName', None) or ''}".strip() or current_user.username

        booking_chat = db.execute(
            select(model.BookingChat).where(model.BookingChat.id == job.booking_chat_id)
        ).scalar_one_or_none()

        if booking_chat:
            history = list(booking_chat.history)
            history.append({
                "role": "system",
                "content": f"{worker_name} placed a bid: Rs {float(bid_amount) if bid_amount is not None else 0}",
                "sender_name": "BID SYSTEM",
            })
            booking_chat.history = history
            db.commit()
            db.refresh(booking_chat)

        bid_payload = {
            "type": "SYSTEM_BID",
            "data": {
                "job_id": job_id,
                "bid_amount": float(match.bid_amount) if match.bid_amount else 0,
                "worker_chat_id": matched_profile.worker_chat_id,
                "worker_name": worker_name,
                "bid_message": match.bid_message or "",
                "booking_chat_id": job.booking_chat_id,
            },
        }
        background_tasks.add_task(
            _broadcast_customer_bid,
            job.booking_chat_id,
            bid_payload,
        )

    return {
        "status": "success",
        "job_id": job_id,
        "bid_amount": match.bid_amount,
        "bid_message": match.bid_message,
        "booking_chat_id": job.booking_chat_id if job else None,
    }


@router.post("/{job_id}/book", summary="Accept selected bid(s) and assign worker to job")
async def book_job(
    job_id: int,
    payload: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    selected_bid_ids = payload.get("selected_bid_ids", [])
    if not selected_bid_ids:
        raise HTTPException(status_code=400, detail="No workers selected for booking.")

    job = db.execute(
        select(model.Job).where(model.Job.id == job_id)
    ).scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the customer who created the job can book a worker.")

    selected_matches = db.execute(
        select(model.JobWorkerMatch).where(
            model.JobWorkerMatch.id.in_(selected_bid_ids),
            model.JobWorkerMatch.job_id == job_id,
        )
    ).scalars().all()

    if not selected_matches:
        raise HTTPException(status_code=404, detail="No valid bids found for the selected IDs.")

    primary_match = selected_matches[0]
    worker_profile = db.execute(
        select(model.WorkerProfile).where(model.WorkerProfile.id == primary_match.worker_id)
    ).scalar_one_or_none()

    if not worker_profile:
        raise HTTPException(status_code=404, detail="Worker profile not found for the selected bid.")

    job.worker_id = worker_profile.user_id
    job.status = "assigned"

    for match in selected_matches:
        match.is_selected = True
        match.is_active = True

    other_matches = db.execute(
        select(model.JobWorkerMatch).where(
            model.JobWorkerMatch.job_id == job_id,
            model.JobWorkerMatch.id.notin_(selected_bid_ids),
        )
    ).scalars().all()

    for match in other_matches:
        match.is_rejected = True
        match.is_active = False

    db.commit()
    db.refresh(job)

    if job.booking_chat_id:
        worker_name = f"{getattr(current_user, 'firstName', None) or ''} {getattr(current_user, 'lastName', None) or ''}".strip() or current_user.username
        booking_chat = db.execute(
            select(model.BookingChat).where(model.BookingChat.id == job.booking_chat_id)
        ).scalar_one_or_none()

        if booking_chat:
            history = list(booking_chat.history)
            history.append({
                "role": "system",
                "content": f"Worker assigned: {worker_profile.user_id} selected for Rs {primary_match.bid_amount or 0}",
                "sender_name": "BID SYSTEM",
            })
            booking_chat.history = history
            db.commit()
            db.refresh(booking_chat)

        bid_payload = {
            "type": "SYSTEM_BID",
            "data": {
                "job_id": job_id,
                "bid_amount": float(primary_match.bid_amount) if primary_match.bid_amount else 0,
                "worker_chat_id": worker_profile.worker_chat_id,
                "worker_name": worker_name,
                "bid_message": primary_match.bid_message or "",
                "booking_chat_id": job.booking_chat_id,
            },
        }
        background_tasks.add_task(
            _broadcast_customer_bid,
            job.booking_chat_id,
            bid_payload,
        )

    return {
        "status": "success",
        "message": "Worker assigned to job successfully.",
        "job_id": job_id,
        "worker_id": job.worker_id,
        "job_status": job.status,
    }


@router.get("/assigned", summary="Fetch jobs assigned to the authenticated worker")
def get_assigned_jobs_for_worker(
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    worker_profile = db.execute(
        select(model.WorkerProfile).where(
            model.WorkerProfile.user_id == current_user.id
        )
    ).scalar_one_or_none()

    if not worker_profile:
        return {"status": "success", "jobs": []}

    stmt = (
        select(model.Job)
        .where(
            model.Job.worker_id == current_user.id,
            model.Job.status == "assigned",
        )
        .order_by(model.Job.updated_at.desc())
    )

    results = db.execute(stmt).scalars().all()

    jobs = [
        {
            "id": row.id,
            "booking_chat_id": row.booking_chat_id,
            "title": row.title,
            "description": row.description,
            "status": row.status,
            "address_text": row.address_text,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "contact_name": row.contact_name,
            "contact_phone": row.contact_phone,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
        for row in results
    ]

    return {"status": "success", "jobs": jobs}
