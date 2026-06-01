# this will create new users and also check if user exists or not
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg2 import IntegrityError
from sqlalchemy.orm import Session
from src.core.oauth2 import get_current_user
from src.database.database import get_db, engine
from src.core import model, schema
from src.core.utils import hash_password

router = APIRouter(
    prefix="/auth", # sets the prefix for all API endpoints same  for this router 
    tags=["auth"], # this is used for documentation purposes, it allows to group User related endpoints
)

model.Base.metadata.create_all(bind=engine)


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=schema.UserOut)
def create_user(new_user:schema.UserCreate, db: Session = Depends(get_db)):
    # hash the password
    user_data = new_user.model_dump()
    user_data["password"] = hash_password(new_user.password)
    
    user = model.User(**user_data) # this creates a new User object using schema, the model_dump() method is used to convert the Pydantic model to a dictionary, ** is use to unpack dictionary and provide equivalent values to User model
    default_role = db.query(model.Role).filter(model.Role.name == "Customer").first()
    if not default_role:
        default_role = model.Role(name="Customer")
        db.add(default_role)
        db.flush()  # This generates an ID for the role without committing yet
        
    # 4. Attach the role to the user
    user.roles.append(default_role) # this will assign the "Customer" role to the new user by querying the Role table for the role with the name "Customer" and appending it to the user's roles list, this is important because we want every new user to have at least the "Customer" role by default, so that they can access the customer-related endpoints in the API.
    # 4. Save to database with targeted error handling
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email or username already exists"
        )
    except Exception as e:
        db.rollback()
        # Catch unexpected errors (like database connection issues) safely
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An unexpected error occurred"
        )
        
    return user