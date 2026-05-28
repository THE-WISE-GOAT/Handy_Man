# this file use to control the API endpoints related to the User model, such as creating a new user, logging in, etc.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database.database import get_db, engine
from src.core import model, schema

router = APIRouter(
    prefix="/users", # sets the prefix for all API endpoints same  for this router 
    tags=["users"], # this is used for documentation purposes, it allows to group User related endpoints
) # creates a new APIRouter instance, which allows us to define API endpoints related to the User model in a separate file, and then include this router in our main application 

model.Base.metadata.create_all(bind=engine) # this will create the tables in the database based on the model.py we defined, if they don't already exist

# to create a new user, we will use the UserCreate schema to validate the data that is sent to the API, and then we will create a new user in the database using the User model, and return the created user using the UserOut schema, which does not include the password field, for security reasons.
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schema.UserOut)
def create_user(new_user:schema.UserCreate, db: Session = Depends(get_db)):
    user = model.User(**new_user.model_dump()) # this creates a new User object using schema, the model_dump() method is used to convert the Pydantic model to a dictionary, ** is use to unpack dictionary and provide equivalent values to User model
    db.add(user) # adds the new user to the database session
    db.commit() # commits the changes to the database, this will save the new user to the database
    db.refresh(user) # this will refresh the user object with the data from the database
    return user # returns the created user, which will be serialized using the UserOut schema, and sent back to the frontend

# to check if user exists or not 
@router.get("/{id}", response_model=schema.UserOut)
def get_user(id: int, db: Session = Depends(get_db)):
    user = db.query(model.User).filter(model.User.id == id).first() # SELECT * FROM users WHERE id = id
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
