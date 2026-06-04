# this page is for the validation of data that is sent to database
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Literal, Optional
from pydantic import Field
from pydantic import BaseModel, Field, EmailStr

# we put value through this schema before it goes to the database, so we can validate that the data is in the correct format and that all required fields are present, this is also used for the API endpoints to validate the data that is sent to the API
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class RoleOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
            
# this is the schema for the data that is sent back to the frontend, we don't want to send the password back to the frontend, so we create a separate schema for that   
class UserOut(BaseModel):
    id: int
    email: EmailStr 
    username: str
    is_active: bool
    created_at: datetime
    roles: list[RoleOut]
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    locationLabel: Optional[str] = None
    accountType: Optional[str] = None

    class Config:
        from_attributes = True
        

class Token(BaseModel):
    access_token:str # this is token that will be used to authenticate the user, it will be generated when the user logs in, and it will be sent back to the frontend, and the frontend will use this token to authenticate the user for subsequent requests to the API
    token_type:str # it will be set as "bearer", which is a common type of token used for authentication, it indicates that the token is a bearer token, which means that the token itself is sufficient to authenticate the user, and no additional credentials are required.
    
    
class TokenData(BaseModel):
    user_id: str | None = None # this is the data that will be contained in the token, it will be used to identify the user when the token is decoded, it will be set to None by default, and it will be populated with the user_id when the token is created.
    
 
# Define the Strict Target JSON Schema for Customer Problem Extraction   
class CustomerProblemSchema(BaseModel):
    problem_category: Literal["plumbing", "electrical", "hvac", "appliance_repair", "other"] = Field(
        description="The general category of the household problem."
    )
    detailed_problem: str = Field(
        description="A concise summary of exactly what is wrong and symptoms mentioned."
    )
    urgency_level: Literal["low", "medium", "high"] = Field(
        description="The priority of the issue based on damage risk or safety issues."
    )
    
# 1. Schema for a single Role
class UserRolesOut(BaseModel):
    roles: list[str]
    
    
    