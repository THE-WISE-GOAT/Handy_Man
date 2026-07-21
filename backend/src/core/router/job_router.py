# routers/job_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.core import model, job_manager
from src.database.database import get_db
from src.core.oauth2 import get_current_user

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("/status/{status_val}")
def get_jobs_by_status_endpoint(
    status_val: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user)
):
    # Fixed: Removed inline imports and redundant 'if not current_user' check
    # Depends(get_current_user) guarantees authentication before this code runs.
    
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
    
    # Fixed: Removed db.commit() here, now safely encapsulated in job_manager
    return {"status": "success", "message": "Job deleted successfully"}