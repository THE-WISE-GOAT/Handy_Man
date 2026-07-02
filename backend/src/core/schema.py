# this page is for the validation of data that is sent to database
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

# ==========================================
# 1. CORE AUTHENTICATION & USER SCHEMAS
# ==========================================

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
    access_token: str 
    token_type: str 
    
class TokenData(BaseModel):
    user_id: str | None = None 

# ==========================================
# 2. DISPATCH PIPELINE TAXONOMY SCHEMAS
# ==========================================

class CategoryMatch(BaseModel):
    """
    One trade's contribution to a job. A job needing more than one trade
    (e.g. a stuck automatic gate needing both structural and electrical
    work) gets one of these per trade, each scoped to only the tags that
    trade would actually perform.
    """
    category: str
    tags: List[str] = Field(default_factory=list)
    is_custom_category: bool

class CustomerProblemSchema(BaseModel):
    """
    Structured-output contract the extraction model fills in after a
    completed interview.
    """
    is_job_request: bool
    categories: List[CategoryMatch] = Field(default_factory=list)
    problem_description: str

# ==========================================
# 3. CHAT INTERVIEW PIPELINE SCHEMAS
# ==========================================

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
        return stripped 

class SessionStartOut(BaseModel):
    """Returned when a new session is created (POST /dispatch/session)."""
    booking_chat_id: int
    ai_response:     str
    turns_remaining: int

class ChatMessageOut(BaseModel):
    """Returned after each chat turn (POST /dispatch/chat)."""
    booking_chat_id:    int
    ai_response:        str
    is_complete:        bool
    current_tags:       List[str]  
    is_job_request:      bool      
    is_custom_category:  bool      
    turns_used:          int
    turns_remaining:      int

class HistoryMessage(BaseModel):
    """A single turn in the client-visible conversation."""
    role:  Literal["user", "assistant"]
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
    categories: List[CategoryMatch] = Field(default_factory=list)
    problem_description: str
    is_complete: bool
    is_job_request: bool

class UserRolesOut(BaseModel):
    roles: list[str]

# ==========================================
# 4. WORKER PIPELINE SCHEMAS
# ==========================================

class WorkerOnboardIn(BaseModel):
    latitude: float
    longitude: float
    job_category: str
    tag: List[str]
    years_experience: int
    operating_radius: float
    additional_metadata: Dict[str, Any]
    ai_assessed_skills_json: Optional[List[str]] = []

class WorkerProfileSchema(BaseModel):
    """Structured-output contract the extraction model fills in after scenario test."""
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

class WorkerSessionStartOut(BaseModel):
    worker_chat_id: int
    ai_response: str
    stage: str

class WorkerChatMessageIn(BaseModel):
    worker_chat_id: int
    message: str

class WorkerChatMessageOut(BaseModel):
    worker_chat_id: int
    ai_response: str
    stage: str                                 
    is_complete: bool
    is_rejected: bool
    scenario_question: Optional[str] = None    
    turns_used: int
    turns_remaining: int

class WorkerChatHistoryOut(BaseModel):
    worker_chat_id: int
    history: List[dict]
    stage: str
    is_complete: bool
    turns_used: int
    turns_remaining: int

class WorkerSummaryOut(BaseModel):
    stage: str
    is_complete: bool
    is_rejected: bool
    rejection_reason: Optional[str] = None
    profile: Optional[WorkerProfileSchema] = None