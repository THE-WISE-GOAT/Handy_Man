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
 
 
class SessionStartOut(BaseModel):
    """Returned when a new session is created (POST /dispatch/session)."""
    booking_chat_id: int
    ai_response:     str
    turns_remaining: int
 
 
class ChatMessageOut(BaseModel):
    """Returned after each chat turn (POST /dispatch/chat)."""
    booking_chat_id:    int
    ai_response:        str
    # FIX: this field was missing. dispatch_chat() in the router builds and
    # returns an "is_complete" key on every call, but because it wasn't
    # declared here, FastAPI's response_model filtering silently dropped it
    # from the actual HTTP response. Without it the client has no reliable
    # way to know the interview just finished and GET /summary is ready to
    # call — which breaks the whole point of this endpoint.
    is_complete:        bool
    current_tags:       List[str]  # Non-empty only on the completion turn
    is_job_request:      bool      # True only on the completion turn, if a real job was found
    is_custom_category:  bool      # True if the category/tags came from the AI fallback, not the static registry
    turns_used:          int
    turns_remaining:      int
 
 
class HistoryMessage(BaseModel):
    """A single turn in the client-visible conversation."""
    role:    Literal["user", "assistant"]
    content: str
 
 
class ChatHistoryOut(BaseModel):
    """Returned by GET /dispatch/{id}/history."""
    booking_chat_id: int
    history:         List[HistoryMessage]
    is_complete:     bool
    turns_used:       int
    turns_remaining: int
 
 
class BookingSummaryOut(BaseModel):
    """Returned by GET /dispatch/{id}/summary once is_complete is True."""
    problem_category:    str
    service_tags:        List[str]
    problem_description: str
    is_complete:          bool
    is_job_request:       bool   # False means: no real job was ever extracted — don't dispatch a worker
    is_custom_category:   bool   # True means: AI-guessed category, route to manual review, not auto-match
 
 
class CustomerProblemSchema(BaseModel):
    """
    FIX: this schema was referenced by src/ai/customer_chat_analyser.py
    (`from src.core.schema import CustomerProblemSchema`) but was never
    actually defined anywhere — that import alone would crash the app on
    startup before a single request could be served.
 
    This is the structured-output contract the extraction model is asked
    to fill in via Ollama's `format=` JSON-schema mode. Field meanings
    match exactly what's described in
    customer_chat_analyser._build_extraction_prompt().
    """
    is_job_request:      bool
    problem_category:    str
    is_custom_category:  bool
    service_tags:        List[str] = Field(default_factory=list)
    problem_description: str
# 1. Schema for a single Role
class UserRolesOut(BaseModel):
    roles: list[str]
    
    
class WorkerOnboardIn(BaseModel):
    latitude: float
    longitude: float
    job_category: str
    tag: List[str]
    years_experience: int
    operating_radius: float
    additional_metadata: Dict[str, Any]
    ai_assessed_skills_json: Optional[List[str]] = []
    
    
    
