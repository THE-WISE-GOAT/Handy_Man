# routers/job_router_3.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.core import model, job_manager, schema
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
    #results = job_manager.get_jobs_by_status(db, current_user.id, status_val, skip, limit)
    from fastapi import HTTPException, status

# Inside your get_jobs_by_status_endpoint:
    if not current_user:
        raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated"
        )

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


@router.get("/for-worker", response_model=schema.MatchedJobsForWorkerOut)
def get_jobs_for_worker(
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user)
):
    worker_profile = db.execute(
        select(model.WorkerProfile).where(
            model.WorkerProfile.user_id == current_user.id,
            model.WorkerProfile.is_complete.is_(True),
        )
    ).scalar_one_or_none()

    if not worker_profile:
        return schema.MatchedJobsForWorkerOut(jobs=[])

    stmt = (
        select(
            model.JobWorkerMatch,
            model.Job,
        )
        .join(model.Job, model.Job.id == model.JobWorkerMatch.job_id)
        .where(
            model.JobWorkerMatch.worker_id == worker_profile.id,
            model.JobWorkerMatch.is_active.is_(True),
        )
        .order_by(model.JobWorkerMatch.match_rank.asc())
    )

    rows = db.execute(stmt).all()

    jobs = []
    for match, job in rows:
        jobs.append(
            schema.WorkerMatchedJobOut(
                job_id=job.id,
                booking_chat_id=job.booking_chat_id,
                title=job.title,
                description=job.description,
                status=job.status,
                categories=job.categories or [],
                address_text=job.address_text,
                latitude=job.latitude,
                longitude=job.longitude,
                match_score=match.match_score,
                match_rank=match.match_rank,
                interested=match.interested,
                matched_count=job.matched_count or 0,
                interested_count=job.interested_count or 0,
            )
        )

    return schema.MatchedJobsForWorkerOut(jobs=jobs)