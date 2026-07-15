# routers/job_router_3.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from src.core import model, job_manager
from src.database.database import get_db
from src.core.oauth2 import get_current_user

# 1. Make sure to import get_db and your manager function
from src.core.job_manager import get_workers_by_category # Adjust path to job_manager if needed

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("/status/{status_val}")
def get_jobs_by_status_endpoint(
    status_val: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user)
):
    results = job_manager.get_jobs_by_status(db, current_user.id, status_val, skip, limit)
    
    # Convert Row objects to dictionaries manually
    formatted_tasks = []
    for row in results:
        formatted_tasks.append({
            "id": row.id,  # Expose the unique primary key to the frontend
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
        })
    
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
    
    db.commit()
    return {"status": "success", "message": "Job deleted successfully"}


# In src/core/router/job_router.py
@router.get("/workers/match")
def match_workers(category: str, db: Session = Depends(get_db)):
    if not category:
        raise HTTPException(status_code=400, detail="Category parameter is required")
    
    # Now a standard synchronous call
    workers = get_workers_by_category(category, db) 
    return workers