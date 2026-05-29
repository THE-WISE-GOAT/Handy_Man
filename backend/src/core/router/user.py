# this file use to control the API endpoints related to the User model, such as creating a new user, logging in, etc.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database.database import get_db
from src.core import model, schema
from src.core.utils import hash_password


router = APIRouter(
    prefix="/users", # sets the prefix for all API endpoints same  for this router 
    tags=["users"], # this is used for documentation purposes, it allows to group User related endpoints
) # creates a new APIRouter instance, which allows us to define API endpoints related to the User model in a separate file, and then include this router in our main application 

# to create a new user, we will use the UserCreate schema to validate the data that is sent to the API, and then we will create a new user in the database using the User model, and return the created user using the UserOut schema, which does not include the password field, for security reasons.
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schema.UserOut)
def create_user(new_user:schema.UserCreate, db: Session = Depends(get_db)):
    # hash the password
    hashed_password= hash_password(new_user.password)
    new_user.password=hashed_password
    
    user = model.User(**new_user.model_dump()) # this creates a new User object using schema, the model_dump() method is used to convert the Pydantic model to a dictionary, ** is use to unpack dictionary and provide equivalent values to User model
    db.add(user) # adds the new user to the database session
    db.commit() # commits the changes to the database, this will save the new user to the database
    db.refresh(user) # this will refresh the user object with the data from the database
    return user # returns the created user, which will be serialized using the UserOut schema, and sent back to the frontend


# to get the current logged in user profile we will use the get_current_user function 
@router.get("/me", status_code=status.HTTP_200_OK, response_model=schema.UserOut)
def get_current_user_info(current_user: model.User = Depends(get_current_user)):
    return current_user


# Gatekeeper logic to see the role of the user that can return ['Customer'] or ['Customer', 'Worker']
@router.get("/{user_id}/roles", status_code=status.HTTP_200_OK, response_model=schema.UserRolesOut)
def get_current_user_roles(user_id: int, current_user: model.User = Depends(get_current_user), db: Session = Depends(get_db)):
    #  Query the targeted user from the database
    user = db.query(model.User).filter(model.User.id == user_id).first()
    
    #  If the user doesn't exist, return a 404 error
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"User with id {user_id} not found"
        )
    
    #  Extract the string names from the user's roles relationship array
    role_names = [role.name for role in user.roles]
    
    #  Return the exact structure expected by your UserRolesOut schema
    return {"roles": role_names}
