from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from geoalchemy2.elements import WKTElement

from src.core import model
from src.core.schema import UserProfileUpdateIn, UserProfileOut
from src.database.database import get_db
from src.core.oauth2 import get_current_user

router = APIRouter(prefix="/userDetails", tags=["UserDetails"])


@router.get("/profile", response_model=UserProfileOut)
def get_user_profile(
    current_user: model.User = Depends(get_current_user)
):
    """
    Retrieves saved user details (contact_name, contact_number, address_text, latitude, longitude)
    from DB for future reference upon login.
    """
    return current_user


@router.put("/profile", response_model=UserProfileOut)
def update_user_profile(
    payload: UserProfileUpdateIn,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user)
):
    """
    Saves user draft profile details (name, contact, address fields) into the users table in DB.
    """
    user = db.query(model.User).filter(model.User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.contact_name is not None:
        user.contact_name = payload.contact_name
    if payload.contact_number is not None:
        user.contact_number = payload.contact_number
    if payload.address_text is not None:
        user.address_text = payload.address_text
    if payload.latitude is not None:
        user.latitude = payload.latitude
    if payload.longitude is not None:
        user.longitude = payload.longitude

    if payload.latitude is not None and payload.longitude is not None:
        user.location = WKTElement(f"POINT({payload.longitude} {payload.latitude})", srid=4326)

    db.commit()
    db.refresh(user)
    return user