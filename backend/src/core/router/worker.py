from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.core import model
from src.database.database import get_db
from src.core.oauth2 import get_current_user

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