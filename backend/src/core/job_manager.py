from sqlalchemy.orm import Session
from src.core import model
import logging

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
    """Fetch jobs for a customer filtered directly by status at the database level."""
    return db.query(model.Job).filter(
        model.Job.customer_id == customer_id,
        model.Job.status == status
    ).offset(skip).limit(limit).all()

def delete_job(db: Session, job_id: int, customer_id: int):
    """
    Marks a job for deletion or deletes it entirely.
    Requires customer_id to prevent unauthorized cross-account deletions.
    """
    db_job = get_job_by_id(db, job_id, customer_id)
    if db_job:
        db.delete(db_job)
        # Note: We do NOT db.commit() here. 
        # The router should call db.commit() to maintain transaction control.
        return True
    return False