# this page is for the validation of data that is sent to database
from pydantic import BaseModel, EmailStr
from datetime import datetime


# we put value through this schema before it goes to the database, so we can validate that the data is in the correct format and that all required fields are present, this is also used for the API endpoints to validate the data that is sent to the API
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    
# this is the schema for the data that is sent back to the frontend, we don't want to send the password back to the frontend, so we create a separate schema for that   
class UserOut(BaseModel):
    id: int
    email: EmailStr 
    username: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True # this is used as database does not return data in the form of a dictionary, but rather as an object, so we need to tell Pydantic to read the data as an object and not a dictionary, this allows us to use the same schema for both input and output data. As, pydantic by default expects data to be in the form of a dictionary, but when we get data from the database, it is in the form of an object, so we need to tell Pydantic to read the data as an object and not a dictionary. This allows us to use the same schema for both input and output data.