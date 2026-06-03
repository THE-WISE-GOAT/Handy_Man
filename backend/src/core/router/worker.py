from select import select

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.core import model
from src.database.database import get_db
from src.core.oauth2 import get_current_user
from src.core.schema import WorkerOnboardIn
from geoalchemy2.functions import ST_Point
from sqlalchemy import select



router = APIRouter(
    prefix="/workers",
    tags=["workers"]
)

@router.post("/apply", status_code=status.HTTP_200_OK)
def apply_worker_role(current_user: model.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Find WORKER role and add it to user if not already present
    worker_role = db.query(model.Role).filter(model.Role.name == "WORKER").first()
    if not worker_role:
        worker_role = model.Role(name="WORKER")
        db.add(worker_role)
        db.flush() 
    
    # Add WORKER role if not already present
    if worker_role not in current_user.roles:
        current_user.roles.append(worker_role)
        db.commit()
        db.refresh(current_user)
    
    return {"message": "Worker role activated successfully"}

@router.post("/onboard", status_code=status.HTTP_200_OK)
def onboard_worker(worker_data: WorkerOnboardIn, current_user: model.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Implementation for onboarding a new worker
    
    # Check if user already has WORKER role
    if any(role.name == "Worker" for role in current_user.roles):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail= "User is already registered as a worker"
        )
    
    # Fetch the role, get official worker role from database
    worker_role = db.execute(
        select(model.Role).where(model.Role.name == "Worker")
    ).scalar_one_or_none()
    
    
    if not worker_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail= "Worker role is not configured in the system"
        )
        
    
    # Geograpgy formatting for PostGIS
    location_point = ST_Point(worker_data.location.longitude, worker_data.location.latitude, srid=4326)
    
    # create new worker profile
    new_worker = model.Worker(
        id=current_user.id,
        location=location_point,
        ai_accessed_skills_json=None, # this will be populated after the AI assessment is done, we can have a separate endpoint to trigger the AI assessment and update this field
    )
    
    try:
        # Add worker role to user
        current_user.roles.append(worker_role)
        # add worker profile to database
        db.add(new_worker)
        db.commit()
        db.refresh(current_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to onboard worker"
        )
        
    return {"message": "Worker onboarded successfully"}