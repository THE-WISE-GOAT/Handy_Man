from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from src.core import model
from src.database.database import get_db
from src.core.oauth2 import get_current_user

router = APIRouter(
    prefix="/workers",
    tags=["workers"]
)

@router.post("/apply", status_code=status.HTTP_200_OK, deprecated=True, summary="Deprecated: Use Onboarding Pipeline")
def apply_worker_role(current_user: model.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    DEPRECATED: Worker role activation is now securely handled by the application state machine.
    Please direct the client to POST /worker-onboarding/initialize to begin the application properly.
    """
    return {
        "message": "Role updates are now safely handled by the onboarding pipeline.",
        "redirect_to": "/worker-onboarding/initialize"
    }

# Future pure worker-profile operational endpoints (stats, shifts, etc.) can be placed here.