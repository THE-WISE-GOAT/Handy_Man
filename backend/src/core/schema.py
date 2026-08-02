# this page is for the validation of data that is sent to database
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TypedDict
from pydantic import BaseModel, EmailStr, Field, field_validator
from src.core import model

class LocationCoordinates(BaseModel):
    longitude: float = Field(..., description="Longitude coordinate (X)", ge=-180, le=180)
    latitude: float = Field(..., description="Latitude coordinate (Y)", ge=-90, le=90)

class CompleteChatIn(BaseModel):
    edited_description: str
    location: LocationCoordinates
    title: str
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    status: str = "pending"
    mode: str = "regular"
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    phone_number: Optional[str] = None

class CreateJobIn(BaseModel):
    title: str
    description: str
    location: LocationCoordinates
    category: Optional[str] = None
    budget: Optional[float] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    status: str = "pending"
    mode: str = "regular"
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    phone_number: Optional[str] = None

class InitializeWorkerAppIn(BaseModel):
    pass

class InitializeWorkerAppOut(BaseModel):
    worker_id: int
    user_id: int
    stage: str
    is_complete: bool
    is_rejected: bool
    worker_chat_id: int | None = None

    class Config:
        from_attributes = True

class SubmitWorkerAppIn(BaseModel):
    worker_chat_id: int
    phone_number: str | None = None
    address_text: str | None = None
    latitude: float | None = None
    longitude: float | None = None

class SubmitWorkerAppOut(BaseModel):
    worker_id: int
    stage: str
    message: str

class WorkerAppStatusOut(BaseModel):
    worker_id: int
    stage: str
    is_complete: bool
    is_rejected: bool
    rejection_reason: str | None = None
    job_category: str
    category_tag: str
    specialities: List[str]
    years_experience: int
    worker_chat_id: int | None = None
    phone_number: str | None = None
    address_text: str | None = None

    class Config:
        from_attributes = True

class AdminPendingAppOut(BaseModel):
    id: int
    user_id: int
    username: str
    email: str
    firstName: str | None = None
    lastName: str | None = None
    stage: str
    is_complete: bool
    is_rejected: bool
    rejection_reason: str | None = None
    job_category: str
    category_tag: str
    specialities: List[str]
    years_experience: int
    worker_chat_id: int | None = None
    phone_number: str | None = None
    address_text: str | None = None
    history: List[dict] | None = None
    profile: dict | None = None

class RejectWorkerIn(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)

class UpdateWorkerProfileIn(BaseModel):
    job_category: Optional[str] = None
    category_tag: Optional[str] = None
    specialities: Optional[List[str]] = None
    specialized_tools_or_equipment: Optional[List[str]] = None
    years_experience: Optional[int] = None
    license_or_certification: Optional[str] = None
    job_description: Optional[str] = None
    emergency_available: Optional[bool] = None
    phone_number: Optional[str] = None
    address_text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class UpdateWorkerProfileOut(BaseModel):
    worker_id: int
    job_category: str
    category_tag: str
    specialities: List[str]
    years_experience: int
    license_or_certification: str | None = None
    job_description: str
    emergency_available: bool
    phone_number: str | None = None
    address_text: str | None = None
    message: str

    class Config:
        from_attributes = True

class UpdateUserIn(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

class ChatMessageOut(BaseModel):
    """Returned after each chat turn (POST /dispatch/chat)."""
    booking_chat_id: int
    ai_response: str
    is_complete: bool
    current_tags: List[str]  
    is_job_request: bool  
    is_custom_category: bool 
    turns_used: int 
    turns_remaining: int 
    
    problem_description: Optional[str] = None  # Allows AI summary to pass to UI
    categories: List[CategoryMatch] = Field(default_factory=list)  # Allows title extraction to pass to UI

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

# this is the schema for the chat functionality, it will be used to validate the data that is sent to the API
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


class HumanChatMessageIn(BaseModel):
    """Payload for human-to-human chat messages."""
    sender: str = Field(
        ...,
        description="Either 'customer' or 'worker' indicating the sender role.",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The message text content.",
    )

    @field_validator("sender")
    @classmethod
    def sender_must_be_valid(cls, v: str) -> str:
        if v not in ("customer", "worker"):
            raise ValueError("sender must be either 'customer' or 'worker'")
        return v

    @field_validator("message")
    @classmethod
    def message_must_have_content(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("message cannot be empty or whitespace-only")
        return stripped


class HumanChatMessageOut(BaseModel):
    """Returned after a human-to-human chat message is sent."""
    booking_chat_id: int
    message: str
    sender: str
    sender_name: Optional[str] = None


# use to display session start response
class SessionStartOut(BaseModel):
    """Returned when a new session is created (POST /dispatch/session)."""
    booking_chat_id: int
    ai_response:     str
    turns_remaining: int
 
# dsupport to display the chat history response after each chat turn
class HistoryMessage(BaseModel):
    """A single turn in the client-visible conversation."""
    role:  Literal["user", "assistant", "customer", "worker"]
    content: str
    sender_name: Optional[str] = None
 
# display the all chat history response 
class ChatHistoryOut(BaseModel):
    """Returned by GET /dispatch/{id}/history."""
    booking_chat_id: int
    history:         List[HistoryMessage]
    is_complete:     bool
    turns_used:      int
    turns_remaining: int
 
 # this is use to disply category for the specific job request
class CategoryMatch(BaseModel):
    category: str
    tags: List[str] = Field(default_factory=list)
    is_custom_category: bool
 
# to display the structured summary mainly needed for the frontend to use dict keys
class BookingSummaryOut(BaseModel):
    """Returned by GET /dispatch/{id}/summary once is_complete is True."""
    categories: List[CategoryMatch] = Field(default_factory=list)
    problem_description: str
    is_complete: bool
    is_job_request: bool
 
# use in the customer_chat_analyser_nvidia.py to validate the data that is sent to the API
class CustomerProblemSchema(BaseModel):
    is_job_request: bool
    categories: List[CategoryMatch] = Field(default_factory=list)
    problem_description: str

 # for now this is just use to get the what is the roles of the user 
# 1. Schema for a single Role
class UserRolesOut(BaseModel):
    roles: list[str]
    
  # for now this support in worker_onboarding.py
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

    # The two layers kept SEPARATE for embedding. job_description above remains
    # the composed, human-readable text (admin views, match cards); these two are
    # what actually get embedded, each into its own worker_skills row.
    #
    # They are populated by extract_worker_profile, not by the extraction model,
    # so they carry defaults for backward compatibility with profiles stored
    # before the split.
    baseline_description: str = ""
    speciality_title: str = ""
    speciality_description: str = ""

    @field_validator(
        "job_description", "license_or_certification", "job_category",
        "baseline_description", "speciality_title", "speciality_description",
        mode="before",
    )
    @classmethod
    def sanitize_string_fields(cls, value: Any) -> str:
        # If AI sends a list, join it into a single string
        if isinstance(value, list):
            return " ".join(str(v) for v in value)
        # Ensure it's a string even if the AI sends an int or other type
        return str(value)

# use to display session start response
class WorkerSessionStartOut(BaseModel):
    worker_chat_id: int
    ai_response: str
    stage: str

# this is the schema for the chat functionality, it will be used to validate the data that is sent to the API
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
    
# ── Find Help (worker matching) ──────────────────────────────────────────────

class WorkerMatchOut(BaseModel):
    worker_chat_id: int
    username: str
    job_category: str
    category_tag: str
    job_description: str
    match_score: float
    matched_skill: Optional[str] = None
    matched_skill_description: Optional[str] = None
    is_interested: bool = False

class FindHelpOut(BaseModel):
    matched_by_category: bool          # True if the category filter was actually used
    category: Optional[str] = None     # the category that was searched (if any)
    workers: List[WorkerMatchOut]
    
    
class WorkerCompleteChatIn(BaseModel):
    location: LocationCoordinates
    phone_number: Optional[str] = None


# ── Add-skill flow (already-verified worker adds another speciality) ──────────

class WorkerSkillOut(BaseModel):
    """One independently matchable capability of a worker."""
    id: int
    skill_type: str          # "baseline" | "speciality"
    title: str
    description: str
    scenario_score: Optional[int] = None
    is_active: bool
    has_vector: bool         # False means it is stored but not yet matchable

    class Config:
        from_attributes = True


class WorkerSkillsListOut(BaseModel):
    worker_chat_id: int
    worker_id: int
    job_category: str
    skills: List[WorkerSkillOut]


class AddSkillStartOut(BaseModel):
    worker_chat_id: int
    ai_response: str
    existing_skills: List[str]
    stage: str               # always "adding_skill"


class AddSkillMessageIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def message_must_have_content(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("message cannot be empty or whitespace-only")
        return stripped


class AddSkillMessageOut(BaseModel):
    worker_chat_id: int
    ai_response: str
    stage: str                              # "adding_skill" | "awaiting_skill_scenario" | "skill_complete" | "skill_declined"
    scenario_question: Optional[str] = None
    # Populated only once a scenario has been graded.
    skill_added: bool = False
    skill_title: Optional[str] = None
    scenario_score: Optional[int] = None


class WorkerExpertiseIn(BaseModel):
    title: str = Field(..., max_length=255, description="E.g., CCTV Installation, Electrical Repair")
    description: str = Field(..., max_length=3000, description="Detailed breakdown of experience or tools owned")

class WorkerExpertiseOut(BaseModel):
    id: int
    worker_id: int
    title: str
    description: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
        
        
# ___________________ for mathcing worker with job request ___________________________
class _MatchDetailRequired(TypedDict):
    worker_profile: model.WorkerProfile
    user: model.User
    score: float
    rank: int
    worker_chat_id: int

class MatchDetail(_MatchDetailRequired, total=False):
    """
    Which single capability actually won the vector search for this worker.

    Split into a total=False half rather than made mandatory so older producers
    (and the reranker's .get() reads) stay valid without every call site having
    to populate them.
    """
    matched_skill_id: Optional[int]
    matched_skill_title: Optional[str]
    matched_skill_description: Optional[str]

class MatchingResult(TypedDict):
    matches: list[MatchDetail]
    worker_chat_ids: list[int]
    count: int

class _MatchedJobDetailRequired(TypedDict):
    booking_chat_id: int
    title: str
    description: str
    score: float
    rank: int

class MatchedJobDetail(_MatchedJobDetailRequired, total=False):
    """matched_skill_title = which of the worker's skills won this job."""
    matched_skill_title: Optional[str]

class WorkerMatchingResult(TypedDict):
    matched_jobs: list[MatchedJobDetail]
    count: int