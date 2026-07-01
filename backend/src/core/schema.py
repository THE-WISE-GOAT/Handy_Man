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
    categories: List[CategoryMatch] = Field(default_factory=list)
    problem_description: str
    is_complete: bool
    is_job_request: bool
 
 
"""
Schema changes needed in src/core/schema.py
=============================================

This file has TWO parts:

  1. A drop-in replacement for CustomerProblemSchema, plus the new
     CategoryMatch model it's built on. Copy these two classes into your
     actual src/core/schema.py, replacing the old CustomerProblemSchema.

  2. A diff guide (bottom of this file, in comments) for the fields you
     need to ADD to your existing ChatMessageOut and BookingSummaryOut
     response models. I only have what dispatch.py reveals those classes
     must already contain — not their actual source — so this is written
     as instructions to apply against your real file, not a file to copy
     wholesale.
"""

from typing import List
from pydantic import BaseModel, Field


class CategoryMatch(BaseModel):
    """
    One trade's contribution to a job. A job needing more than one trade
    (e.g. a stuck automatic gate needing both structural and electrical
    work) gets one of these per trade, each scoped to only the tags that
    trade would actually perform — never a flat list of tags dumped under
    a single category.

    category:
        Lowercase, hyphenated trade name. Preferably an exact
        SERVICE_REGISTRY key; allowed to be freshly invented when the job
        genuinely doesn't fit any existing one.
    tags:
        1-3 short, lowercase, hyphenated tags describing the SPECIFIC part
        of the task this trade would handle. May be registry tags,
        invented tags, or a mix — tags are never dropped just because
        they aren't in the static registry. Precision beats registry
        membership.
    is_custom_category:
        True if EITHER this category is not an exact registry match OR any
        of its tags had to be invented. False only when both the category
        and every tag are exact, verified registry matches. Informational —
        tells the dispatch layer "this trade's match needs a closer look,"
        not a gate that discards anything.
    """
    category: str
    tags: List[str] = Field(default_factory=list)
    is_custom_category: bool


class CustomerProblemSchema(BaseModel):
    """
    Structured-output contract the extraction model fills in after a
    completed interview. Field meanings match exactly what's described in
    chat_analyser_nvidia._build_extraction_prompt().

    is_job_request:
        False if the conversation never produced a genuine dispatchable
        job (small talk, off-topic, refused/abandoned). `categories` and
        `problem_description` are blanked out in that case — there is
        nothing to dispatch.
    categories:
        1-3 CategoryMatch entries, one per trade genuinely needed for this
        job, ordered with the most central trade first. This REPLACES the
        old problem_category + secondary_categories + service_tags +
        top-level is_custom_category fields — every piece of trade/tag/
        custom-category data now lives here, scoped per trade instead of
        flattened under one primary category. Empty list if
        is_job_request is false.
    problem_description:
        One plain-language sentence summarizing what the customer
        reported. Empty string if is_job_request is false.
    """
    is_job_request: bool
    categories: List[CategoryMatch] = Field(default_factory=list)
    problem_description: str


# ---------------------------------------------------------------------------
# DIFF GUIDE — apply against your actual src/core/schema.py
# ---------------------------------------------------------------------------
#
# Your ChatMessageOut and BookingSummaryOut response models currently expose
# fields from the old flat CustomerProblemSchema shape. Based on what
# dispatch.py constructs and returns, here's what each one needs:
#
#   class ChatMessageOut(BaseModel):
#       ...                                      # whatever else it already has
#       categories: List[CategoryMatch] = []      # NEW — full per-trade breakdown,
#                                                  # use this for actual worker routing
#       current_tags: List[str]                   # already exists — now a flattened
#                                                  # union of tags across ALL trades,
#                                                  # not just one category
#       is_custom_category: bool                  # already exists — now means "true
#                                                  # if ANY entry in `categories` is
#                                                  # custom", not a single category's flag
#
#       (remember to `from src.core.schema import CategoryMatch` or define it
#       in the same module before referencing it here)
#
#   class BookingSummaryOut(BaseModel):
#       ...                                      # whatever else it already has
#       categories: List[CategoryMatch] = []      # NEW — replaces problem_category,
#                                                  # service_tags, and the old
#                                                  # top-level is_custom_category;
#                                                  # each entry carries its own
#                                                  # is_custom_category now
#
# SessionStartOut and ChatHistoryOut are untouched by this change — neither
# one ever carried category/tag data.
# ---------------------------------------------------------------------------
 
    
    
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
    
    
    
