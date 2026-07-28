from sqlalchemy.orm import Session
from src.core import model
import logging
from sqlalchemy import text
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# --- EXISTING UPSERT FUNCTIONS ---

def upsert_chat_data(db: Session, booking_chat_id: int, user_id: int, fields: dict):
    """Handles analytical record persistence."""
    db_profile = db.query(model.CustomerChatData).filter(
        model.CustomerChatData.booking_chat_id == booking_chat_id
    ).first()

    if db_profile:
        for key, value in fields.items():
            setattr(db_profile, key, value)
    else:
        db_profile = model.CustomerChatData(
            user_id=user_id,
            booking_chat_id=booking_chat_id,
            **fields
        )
    db.add(db_profile)
    return db_profile

def upsert_job(db: Session, booking_chat_id: int, user_id: int, fields: dict):
    """Handles operational ticket persistence by booking_chat_id."""
    db_job = db.query(model.Job).filter(
        model.Job.booking_chat_id == booking_chat_id
    ).first()

    if db_job:
        for key, value in fields.items():
            setattr(db_job, key, value)
    else:
        db_job = model.Job(booking_chat_id=booking_chat_id, customer_id=user_id, **fields)
        db.add(db_job)

    db.flush()
    return db_job

# --- NEW JOB CRUD & FILTER FUNCTIONS ---

def get_job_by_id(db: Session, job_id: int, customer_id: int):
    """Fetch a specific job, ensuring it belongs to the requesting customer."""
    return db.query(model.Job).filter(
        model.Job.id == job_id,
        model.Job.customer_id == customer_id
    ).first()

def get_all_jobs_for_customer(db: Session, customer_id: int, skip: int = 0, limit: int = 50):
    """Fetch all jobs for a specific customer with pagination."""
    return db.query(model.Job).filter(
        model.Job.customer_id == customer_id
    ).offset(skip).limit(limit).all()

def get_jobs_by_status(db: Session, customer_id: int, status: str, skip: int = 0, limit: int = 50):
    """Fetch only specific job fields for a customer filtered by status."""
    return db.query(
        model.Job.id,                # Ensure the primary key is passed to the frontend
        model.Job.booking_chat_id,
        model.Job.title,
        model.Job.description,
        model.Job.status,
        model.Job.contact_name,
        model.Job.contact_phone,
        model.Job.attachments,
        model.Job.address_text,
        model.Job.latitude,  
        model.Job.longitude,
        model.Job.updated_at
    ).filter(
        model.Job.customer_id == customer_id,
        model.Job.status == status
    ).offset(skip).limit(limit).all()
# In job_manager.py

def delete_job(db: Session, job_id: int, customer_id: int):
    """
    Deletes a job entirely and commits the transaction.
    Requires customer_id to prevent unauthorized cross-account deletions.
    """
    db_job = get_job_by_id(db, job_id, customer_id)
    if db_job:
        db.delete(db_job)
        db.commit()  # Fixed: Added commit here to finalize the transaction
        return True
    return False

def create_job_direct(db: Session, user_id: int, fields: dict) -> model.Job:
    """Create a Job record directly without a booking_chat_id."""
    db_job = model.Job(customer_id=user_id, **fields)
    db.add(db_job)
    db.flush()
    return db_job

def get_workers_by_category(category: str, db: Session):
    """Fetches workers by category using the ORM with error raising."""
    try:
        # Fixed: Swapped raw SQL for SQLAlchemy ORM
        workers = db.query(
            model.WorkerProfile.id,
            model.WorkerProfile.job_category.label('category'),
            model.WorkerProfile.latitude,
            model.WorkerProfile.longitude
        ).filter(
            model.WorkerProfile.job_category.ilike(category)
        ).all()
        
        return [{"id": w.id, "category": w.category, "latitude": w.latitude, "longitude": w.longitude} for w in workers]
    except Exception as e:
        logger.error(f"Failed to fetch workers by category '{category}': {e}")
        # Fixed: Raise HTTPException so the API doesn't silently return empty lists on failure
        raise HTTPException(status_code=500, detail="Database query failed while fetching workers.")