# this file will handle the OAuth2, it will create the token, verify the token and handle the login logic
# this file provide special token instead of actual password

from fastapi.security import OAuth2PasswordBearer # this grabs token from the request header and verifies it if that is token or not, if not returns 401 error
from src.configuration.config import settings
from datetime import datetime, timedelta, timezone
import jwt # jwt -> JSON Web Token, acts as keycard contains header, payload, and signature use for securely transmitting
from fastapi import HTTPException, status, Depends
from src.core.schema import TokenData
from sqlalchemy.orm import Session
from src.database.database import get_db
from src.core import model

oauth2_schema = OAuth2PasswordBearer(tokenUrl="login/") # this creates an instance which will be used to handle the token, and tokenUrl is the endpoint where the user will send their username and password to get a token

SECRET_KEY =  settings.SECRET_KEY 
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# it's like printing new keycard for the user, it will contain the user_id and the expiry time of the token, so that we can verify if the token is still valid or not when the user makes a request to a protected endpoint.
# this function will create a token for the user, it will take a dictionary of data, and return a token that can be used to authenticate the user in future requests
def create_access_token(data: dict):
    to_encode =data.copy() # creatind copy of data to avoid modifying the original data
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES) # for expiry it will be current time + the number of minutes specified in the settings
    to_encode.update({"exp": expire}) # this add the expiry time to the token data
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM) # this will encode the token using the secret key and the algorithm specified in the settings
    return encoded_jwt # this will return the encoded token, which can be sent back to the frontend and used for authentication in future requests

# it's like scanner for the keycard, it will check if the token is valid or not, and if it is valid, it will return the data contained in the token, which we can use to identify the user in future requests. If the token is not valid, it will raise an error.
# this function will verify the token, it will take a token as input, and return the data contained in the token if the token is valid, otherwise it will raise an error
def verify_access_token(token: str, credentials_exception: HTTPException):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) # this will decode the token using the secret key and the algorithm specified in the settings, if the token is invalid, it will raise an error
        id = str(payload.get("user_id")) # this will get the user_id from the token payload, which we will use to identify the user in future requests
        if id is None:
            raise credentials_exception
        token_data = TokenData(user_id=id) # this is about validating token data, double checking if the token contains the user_id, if it does not contain the user_id, it will raise an error
        
    except jwt.PyJWTError: # this wioll catch error occured during decoding the toke and raise error 
        raise credentials_exception
    
    return token_data # this will return the token data, which contains the user_id, if the token is valid


# it's like the security guard at the entrance, it will check if the user has a valid token before allowing them to access protected endpoints, it will use the verify_access_token function to check if the token is valid, and if it is valid, it will return the user_id contained in the token, which we can use to identify the user in future requests. If the token is not valid, it will raise an error.
def get_current_user(token:str = Depends(oauth2_schema), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    token_data = verify_access_token(token, credentials_exception) # this will verify the token and return the token data, which contains the user_id, if the token is valid, otherwise it will raise an error
    user = db.query(model.User).filter(model.User.id == token_data.user_id).first() # this will query the database to get the user with the user_id contained in the token, if the user does not exist, it will return None
    return user # this hands entire user profile

# Flow of this file:
# 1. User sends a request to the login endpoint with their username and password
# 2. If the username and password are correct, the login endpoint will call the create_access_token function to create a token for the user, and return the token to the frontend
# 3. The frontend will store the token and any subsequent request will include the token in the request header to access protected endpoints
# 4. When the user makes a request to a protected endpoint, the get_current_user function will be called, which will use the verify_access_token function to check if the token is valid, and if it is valid, it will return the user_id contained in the token, which we can use to identify the user in future requests. If the token is not valid, it will raise an error and prevent access to the protected endpoint.