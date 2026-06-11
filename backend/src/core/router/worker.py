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
    worker_role = db.query(model.Role).filter(model.Role.name == "worker").first()
    if not worker_role:
        worker_role = model.Role(name="worker")
        db.add(worker_role)
        db.flush()
    
    if worker_role not in current_user.roles:
        current_user.roles.append(worker_role)
        db.commit()
        db.refresh(current_user)
    
    return {"message": "Worker role activated successfully"}

  #  remaining to maintain the worker profile after applying for the worker role