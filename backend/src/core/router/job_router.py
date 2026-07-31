# routers/job_router.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from src.core import model, schema, job_manager, matching_manager
from src.database.database import get_db
from src.core.oauth2 import get_current_user
from src.ai.worker_chat_analyser_nvidia import get_worker_description_embedding
import logging
import httpx

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)

DEFAULT_SEARCH_RADIUS_METERS = 60_000  # 60 km — hard cutoff


async def _get_address_from_coords(lat: float, lng: float) -> str:
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"lat": lat, "lon": lng, "format": "json", "addressdetails": 1}
    headers = {"User-Agent": "WorkerVerificationApp/1.0 (contact: admin@yourdomain.com)"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers, timeout=8.0)
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


# @router.post("", status_code=status.HTTP_201_CREATED, summary="Create a job directly without AI chat")
# async def create_job_direct_endpoint(
#     payload: schema.CreateJobIn,
#     background_tasks: BackgroundTasks,
#     db: Session = Depends(get_db),
#     current_user: model.User = Depends(get_current_user),
# ):
#     lng = payload.location.longitude
#     lat = payload.location.latitude
#     wkt_point = f"POINT({lng} {lat})"

#     job_desc = payload.description.strip()
#     if not job_desc:
#         job_desc = f"{payload.title}: {payload.contact_name or ''}".strip()
#     if not job_desc:
#         raise HTTPException(status_code=400, detail="Job description is required.")

#     try:
#         embedding_vector = await get_worker_description_embedding(job_desc)
#     except Exception as exc:
#         logger.error(f"Embedding error: {exc}")
#         raise HTTPException(status_code=502, detail="Failed to generate job embedding.")

#     address_text = await _get_address_from_coords(lat, lng)

#     categories = []
#     if payload.category:
#         categories = [{"category": payload.category, "tags": [], "is_custom_category": False}]

#     job_fields = {
#         "title": payload.title,
#         "description": job_desc,
#         "status": payload.status,
#         "is_job_request": True,
#         "categories": categories,
#         "contact_name": payload.contact_name,
#         "contact_phone": payload.contact_phone,
#         "mode": payload.mode,
#         "attachments": payload.attachments,
#         "latitude": lat,
#         "longitude": lng,
#         "location": wkt_point,
#         "description_vector": embedding_vector,
#         "address_text": address_text,
#     }

#     try:
#         job_data = job_manager.create_job_direct(db, current_user.id, job_fields)
#         db.commit()
#     except Exception as e:
#         db.rollback()
#         logger.error(f"Job creation failed: {e}")
#         raise HTTPException(status_code=500, detail="Database update failed.")

#     try:
#         matching_result = matching_manager.create_matches_for_job(
#             db=db,
#             job_id=job_data.id,
#             query_vector=embedding_vector,
#             customer_location=wkt_point,
#             radius_meters=DEFAULT_SEARCH_RADIUS_METERS,
#         )
#         db.commit()
#     except Exception as engine_err:
#         db.rollback()
#         logger.error(f"Matching Engine failed: {engine_err}")
#         raise HTTPException(status_code=500, detail="Failed to compile marketplace matches.")

#     job_payload = {
#         "booking_chat_id": None,
#         "title": payload.title,
#         "description": job_desc,
#     }

#     worker_chat_ids = matching_result.get("worker_chat_ids", [])
#     if worker_chat_ids:
#         background_tasks.add_task(_broadcast_notifications, worker_chat_ids, job_payload)

#     return {
#         "status": "success",
#         "message": f"Job created. Established {matching_result.get('count', 0)} matches successfully.",
#         "job_id": job_data.id,
#     }


@router.get("/status/{status_val}")
def get_jobs_by_status_endpoint(
    status_val: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user)
):
    results = job_manager.get_jobs_by_status(db, current_user.id, status_val, skip, limit)
    
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
            "updated_at": row.updated_at
        }
        for row in results
    ]
    
    return {"status": "success", "tasks": formatted_tasks}

@router.delete("/{job_id}", summary="Delete a specific job")
def delete_job_endpoint(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user)
):
    success = job_manager.delete_job(db, job_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or unauthorized")
    
    return {"status": "success", "message": "Job deleted successfully"}