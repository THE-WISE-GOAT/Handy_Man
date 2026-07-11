# this page is for the validation of data that is sent to database
from datetime import datetime
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
    roles: List[RoleOut]
    firstName: Optional[str] = None
    lastName: Optional[str] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str 
    token_type: str 
    
class TokenData(BaseModel):
    user_id: Optional[str] = None

class UserRolesOut(BaseModel):
    """Schema for returning user role assignments."""
    roles: List[str]

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
    completed interview. Used also in customer_chat_analyser_nvidia.py.
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
    ai_response: str
    turns_remaining: int
 
class ChatMessageOut(BaseModel):
    """Returned after each chat turn (POST /dispatch/chat)."""
    booking_chat_id: int
    ai_response: str
    is_complete: bool
    current_tags: List[str]  # problem related tags
    is_job_request: bool  # True only on the completion turn, if a real job was found
    is_custom_category: bool # True if the category/tags came from the AI fallback, not the static registry
    turns_used: int # number of turns used in the chat session
    turns_remaining: int # number of turns remaining in the chat session

class HistoryMessage(BaseModel):
    """A single turn in the client-visible conversation."""
    role: Literal["user", "assistant"]
    content: str

class ChatHistoryOut(BaseModel):
    """Returned by GET /dispatch/{id}/history."""
    booking_chat_id: int
    history: List[HistoryMessage]
    is_complete: bool
    turns_used: int
    turns_remaining: int

class BookingSummaryOut(BaseModel):
    """Returned by GET /dispatch/{id}/summary once is_complete is True."""
    categories: List[CategoryMatch] = Field(default_factory=list)
    problem_description: str
    is_complete: bool
    is_job_request: bool

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
    """Returned after each worker chat turn."""
    worker_chat_id: int
    ai_response: str
    stage: str     # "interviewing" | "awaiting_scenario_answer" | "complete"
    is_complete: bool
    is_rejected: bool
    scenario_question: Optional[str] = None  
    turns_used: int
    turns_remaining: int

class WorkerChatHistoryOut(BaseModel):
    worker_chat_id: int
    history: List[Dict[str, Any]]
    stage: str
    is_complete: bool
    turns_used: int
    turns_remaining: int

class WorkerSummaryOut(BaseModel):
    """Displays structured summary for the frontend to digest via dict keys."""
    stage: str
    is_complete: bool
    is_rejected: bool
    rejection_reason: Optional[str] = None
    profile: Optional[WorkerProfileSchema] = None   

# ==========================================
# 5. WORKER MATCHING / FIND HELP SCHEMAS
# ==========================================

class WorkerMatchOut(BaseModel):
    worker_chat_id: int
    username: str
    job_category: str
    category_tag: str
    job_description: str
    match_score: float  # 1.0 = near-identical meaning, 0 = unrelated

class FindHelpOut(BaseModel):
    matched_by_category: bool          # True if the category filter was actually used
    category: Optional[str] = None     # the category that was searched (if any)
    workers: List[WorkerMatchOut]
    profile: Optional[WorkerProfileSchema] = None