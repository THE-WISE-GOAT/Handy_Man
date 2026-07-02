# this page is for the validation of data that is sent to database
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Any, List, Literal, Optional, Dict
from pydantic import Field
from pydantic import BaseModel, Field, EmailStr



# we put value through this schema before it goes to the database, so we can validate that the data is in the correct format and that all required fields are present, this is also used for the API endpoints to validate the data that is sent to the API
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None

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

    class Config:
        from_attributes = True
        

class Token(BaseModel):
    access_token:str # this is token that will be used to authenticate the user, it will be generated when the user logs in, and it will be sent back to the frontend, and the frontend will use this token to authenticate the user for subsequent requests to the API
    token_type:str # it will be set as "bearer", which is a common type of token used for authentication, it indicates that the token is a bearer token, which means that the token itself is sufficient to authenticate the user, and no additional credentials are required.
    
    
class TokenData(BaseModel):
    user_id: str | None = None # this is the data that will be contained in the token, it will be used to identify the user when the token is decoded, it will be set to None by default, and it will be populated with the user_id when the token is created.
    

# this is the schema for the chat functionality, it will be used to validate the data that is sent to the API, and it will be used to validate the data
class ChatMessageIn(BaseModel):
    """Payload the client sends on each chat turn."""
    booking_chat_id: int = Field(
        ...,
        description="The session ID returned by POST /dispatch/session.",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The customer's raw message text.",
    )
 
    @field_validator("message")
    @classmethod
    def message_must_have_content(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("message cannot be empty or whitespace-only")
        return stripped  # normalised once, here — not re-stripped downstream
 
 # use to display session start response
class SessionStartOut(BaseModel):
    """Returned when a new session is created (POST /dispatch/session)."""
    booking_chat_id: int
    ai_response:     str
    turns_remaining: int
 
 # display the chat message response after each chat turn
class ChatMessageOut(BaseModel):
    """Returned after each chat turn (POST /dispatch/chat)."""
    booking_chat_id: int
    ai_response: str
    is_complete: bool
    current_tags: List[str]  # problem related tags
    is_job_request: bool  # True only on the completion turn, if a real job was found
    is_custom_category: bool # True if the category/tags came from the AI fallback, not the static registry
    turns_used: int # number of turns used in the chat session
    turns_remaining:  int # number of turns remaining in the chat session
 
 # dsupport to display the chat history response after each chat turn
class HistoryMessage(BaseModel):
    """A single turn in the client-visible conversation."""
    role:    Literal["user", "assistant"]
    content: str
 
 # display the all chat history response 
class ChatHistoryOut(BaseModel):
    """Returned by GET /dispatch/{id}/history."""
    booking_chat_id: int
    history:         List[HistoryMessage]
    is_complete:     bool
    turns_used:       int
    turns_remaining: int
 
 # to display the structured summary mainly needed for the frontend to use dict keys
class BookingSummaryOut(BaseModel):
    """Returned by GET /dispatch/{id}/summary once is_complete is True."""
    categories: List[CategoryMatch] = Field(default_factory=list)
    problem_description: str
    is_complete: bool
    is_job_request: bool
 
 # this is use to disply category for the specific job request
class CategoryMatch(BaseModel):
    category: str
    tags: List[str] = Field(default_factory=list)
    is_custom_category: bool

# use in the customer_chat_analyser_nvidia.py to validate the data that is sent to the API
class CustomerProblemSchema(BaseModel):
    is_job_request: bool
    categories: List[CategoryMatch] = Field(default_factory=list)
    problem_description: str


 # for now this is just use to get the what is the roles of the user 
# 1. Schema for a single Role
class UserRolesOut(BaseModel):
    roles: list[str]
    
 # for now this support in worker.py   
class WorkerOnboardIn(BaseModel):
    latitude: float
    longitude: float
    job_category: str
    tag: List[str]
    years_experience: int
    operating_radius: float
    additional_metadata: Dict[str, Any]
    ai_assessed_skills_json: Optional[List[str]] = []





### schemas for the worker chat functionality

# use in the worker_chat_analyser_nvidia.py to validate the data that is sent to the API
class WorkerProfileSchema(BaseModel):
    job_category: str
    category_tag: str
    is_custom_category: bool
    specialities: List[str] = Field(default_factory=list)
    years_experience: int
    license_or_certification: str
    specialized_tools_or_equipment: List[str] = Field(default_factory=list)
    job_description: str
    emergency_available: bool
    has_verified_specialty: bool
    scenario_passed: bool
    scenario_score: int

# use to display session start response
class WorkerSessionStartOut(BaseModel):
    worker_chat_id: int
    ai_response: str
    stage: str

# this is the schema for the chat functionality, it will be used to validate the data that is sent to the API, and it will be used to validate the data
class WorkerChatMessageIn(BaseModel):
    worker_chat_id: int
    message: str

# this display the chat message response after each chat turn
class WorkerChatMessageOut(BaseModel):
    worker_chat_id: int
    ai_response: str
    stage: str     # "interviewing" | "awaiting_scenario_answer" | "complete"
    is_complete: bool
    is_rejected: bool
    scenario_question: Optional[str] = None  
    turns_used: int
    turns_remaining: int

#  display the all chat history response 
class WorkerChatHistoryOut(BaseModel):
    worker_chat_id: int
    history: List[dict]
    stage: str
    is_complete: bool
    turns_used: int
    turns_remaining: int

# to display the structured summary mainly needed for the frontend to use dict keys
class WorkerSummaryOut(BaseModel):
    stage: str
    is_complete: bool
    is_rejected: bool
    rejection_reason: Optional[str] = None
    profile: Optional[WorkerProfileSchema] = None   