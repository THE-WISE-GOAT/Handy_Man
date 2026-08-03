# this file use to control the API endpoints related to the User model, such as creating a new user, logging in, etc.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database.database import get_db
from src.core import model, schema
from src.core.utils import hash_password
from src.core.oauth2 import get_current_user

router = APIRouter(
    prefix="/users",  # sets the prefix for all API endpoints same  for this router
    tags=[
        "users"
    ],  # this is used for documentation purposes, it allows to group User related endpoints
)  # creates a new APIRouter instance, which allows us to define API endpoints related to the User model in a separate file, and then include this router in our main application

# to create a new user, we will use the UserCreate schema to validate the data that is sent to the API, and then we will create a new user in the database using the User model, and return the created user using the UserOut schema, which does not include the password field, for security reasons.


# to get the current logged in user profile we will use the get_current_user function
@router.get("/me", status_code=status.HTTP_200_OK, response_model=schema.UserOut)
def get_current_user_info(current_user: model.User = Depends(get_current_user)):
    return current_user


@router.put("/me", status_code=status.HTTP_200_OK, response_model=schema.UserOut)
def update_current_user_info(
    payload: schema.UpdateUserIn,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    update_data = payload.model_dump(exclude_unset=True)

    if "password" in update_data:
        hashed_password = hash_password(update_data["password"])
        current_user.password = hashed_password
        del update_data["password"]

    for field, value in update_data.items():
        if hasattr(current_user, field):
            setattr(current_user, field, value)

    try:
        db.commit()
        db.refresh(current_user)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile.",
        )

    return current_user


# Quick role promotion: instantly promote the current user to a Worker (role id 2)
# by attaching the worker role. No interview/onboarding steps required.
# Role id mapping: 1 = Customer, 2 = Worker, 3 = Admin.
@router.post(
    "/become-worker", status_code=status.HTTP_200_OK, response_model=schema.UserOut
)
def become_worker(
    current_user: model.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    # Reuse the existing Worker role (case-insensitive: "WORKER" / "worker" / "Worker").
    worker_role = db.query(model.Role).filter(model.Role.name.ilike("worker")).first()
    if not worker_role:
        worker_role = model.Role(name="worker")
        db.add(worker_role)
        db.flush()

    already_worker = any(
        role.name and role.name.lower() == "worker" for role in current_user.roles
    )

    if not already_worker:
        current_user.roles.append(worker_role)
        db.commit()
        db.refresh(current_user)

    return current_user


def _is_admin(user: model.User) -> bool:
    return any(role.name and role.name.lower() == "admin" for role in user.roles)


# Admin-only: list every user (with roles) so the admin dashboard can show
# all customers and workers. Role id mapping: 1 = Customer, 2 = Worker, 3 = Admin.
@router.get("/", status_code=status.HTTP_200_OK, response_model=list[schema.UserOut])
def list_users(
    current_user: model.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return db.query(model.User).all()


# Gatekeeper logic to see the role of the user that can return ['Customer'] or ['Customer', 'Worker']
@router.get(
    "/{user_id}/roles",
    status_code=status.HTTP_200_OK,
    response_model=schema.UserRolesOut,
)
def get_current_user_roles(
    user_id: int,
    current_user: model.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    #  Query the targeted user from the database
    user = db.query(model.User).filter(model.User.id == user_id).first()

    #  If the user doesn't exist, return a 404 error
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )

    #  Extract the string names from the user's roles relationship array
    role_names = [role.name for role in user.roles]

    #  Return the exact structure expected by your UserRolesOut schema
    return {"roles": role_names}
