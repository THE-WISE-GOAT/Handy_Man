from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.core import model, job_manager
from src.database.database import get_db
from src.core.oauth2 import get_current_user

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("/status/{status_val}", summary="Fetch jobs by status dynamically")
def get_jobs_by_status_endpoint(
    status_val: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user)
):
    """
    Fetches jobs for the current user, filtered dynamically by status.
    Example: /jobs/status/pending, /jobs/status/completed
    """
    tasks = job_manager.get_jobs_by_status(db, current_user.id, status_val, skip, limit)
    
    # Return in the format your frontend (bookingsZlice) expects
    return {
        "status": "success",
        "tasks": tasks
    }

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