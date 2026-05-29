from fastapi import APIRouter, Depends, HTTPException, status
from src.core.schema import Token
from src.core import utils
from src.core import model
from sqlalchemy.orm import Session
from src.database.database import get_db
from fastapi.security import OAuth2PasswordRequestForm # this is use to handle login form that is easily done using username and password
from src.core.oauth2 import create_access_token # this is use to create a token for the user after successful login, so that the user can use that token to access protected endpoints in future requests

router = APIRouter(
    prefix="/login", # sets the prefix for API endpoints
    tags=["login"]  
)

# this handles the login logic, we will check if the user exists in the database, and  if it is correct, we will generate a token and return it to the frontend, if it is not correct, we will return an error message
@router.post("/", response_model=Token)
def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db : Session= Depends(get_db)):
    user=db.query(model.User).filter(model.User.username == user_credentials.username).first() # SELECT * FROM users WHERE username = user_credentials.username
    if not user: # if user does not exist, we will return an error message
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not utils.verify_password(user_credentials.password, user.password): # calls verify_password() to check if the provided password matches the hashed password stored in the database, if it does not match, we will return an error message
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Incorrect password")
    access_token = create_access_token(data={"user_id": user.id}) # this will create a token for the user after successful login
    return {"access_token": access_token, "token_type": "bearer"} # this will return the token and its type to the frontend