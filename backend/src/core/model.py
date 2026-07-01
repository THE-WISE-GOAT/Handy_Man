# This file defines the database schema for the User model using SQLAlchemy. This is use for components of database components

from typing import List, Optional
import uuid

from pydantic import BaseModel, Field

from src.database.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Boolean, ForeignKey, Enum, Text, ARRAY, Float, text
from sqlalchemy.sql.sqltypes import TIMESTAMP, UUID, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum
from datetime import datetime
from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import JSON
from sqlalchemy import DateTime, JSON, func  
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    firstName: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lastName: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default='TRUE')
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default="now()")
      
    
    # THE RELATIONSHIP LINK FOR USER
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary="user_roles",       # Maps to the __tablename__ string of UserRole
        back_populates="users",       # Matches the attribute name inside the Role class
        lazy="selectin"               # CRITICAL FOR ASYNCPG: Pre-loads data safely, lazy="selectin" is crucial here. It tells SQLAlchemy to fetch the user's roles automatically so they are ready when your endpoint asks for them (Mainly to have asysnc process)
    )
    
class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)

    # THE RELATIONSHIP LINK FOR ROLE
    users: Mapped[List["User"]] = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles",
        lazy="selectin"
    )

class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)

"""
SQLAlchemy model for a single dispatch chat session.

NOTE: the only thing src/routers/dispatch.py relies on here is the
`user_id` foreign key column below. The router previously referenced a
`customer_id` column that doesn't exist on this model — see dispatch.py
for the fix.
"""

from typing import List

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base  # adjust to match your project's declarative base import


"""
Changes needed in your model.py (the BookingChat class)
==========================================================

Replaces problem_category (String) + service_tags (ARRAY(String)) +
is_custom_category (Boolean) with a single `categories` JSONB column that
mirrors the new CategoryMatch list shape from src/core/schema.py:

    [
      {"category": "construction", "tags": ["gate-repair"], "is_custom_category": true},
      {"category": "electrical",   "tags": ["electric-motor-replacement"], "is_custom_category": true}
    ]

`is_job_request` is unchanged — it's still a simple top-level bool.

Note: your original is_job_request column comment says it's "set to true
when the user clicks the Submit Job Request button in the frontend" — that
doesn't match how dispatch.py actually sets it (from the extraction
pipeline's result, not a button click). Worth a quick check on whether that
comment is stale documentation or describes a different flag you haven't
wired up yet — left as-is here since I can't tell which from the code alone.

Apply this as a diff against your real model.py; this isn't a full file
since I don't have your imports, Base class, or the rest of BookingChat's
neighbors.
"""

# Required import in your model.py, if not already present:
# from sqlalchemy.dialects.postgresql import JSONB


class BookingChat(Base):  # (Base) — keep your existing base class
    __tablename__ = "booking_chats"

    id: Mapped[int]= mapped_column(primary_key=True, index=True)
    user_id: Mapped[int]= mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    history: Mapped[list[dict]] = mapped_column(JSON, default=list) 
    is_complete: Mapped[bool]  = mapped_column(Boolean, server_default='FALSE', nullable=False)
    is_job_request: Mapped[bool]   = mapped_column(Boolean, server_default='FALSE', nullable=False)

    # REPLACES problem_category (String) + service_tags (ARRAY(String)) +
    # is_custom_category (Boolean). Each job can now span more than one
    # trade, and each trade's tags stay scoped to that trade instead of
    # being flattened under one category — see CategoryMatch in
    # src/core/schema.py. First entry in the list is the most central
    # category for the job.
    categories: Mapped[list[dict]]   = mapped_column(JSONB, nullable=True)

    problem_description: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Actual SQLAlchemy column definitions to copy in (same types you already
# use elsewhere in this file — String/ARRAY swapped out, JSONB import added):
# ---------------------------------------------------------------------------
#
#   categories: Mapped[List[dict]] = mapped_column(JSONB, nullable=True)
#   # delete: problem_category, service_tags, is_custom_category
#
# Then generate + apply the matching Alembic migration — see
# alembic_migration_multi_category.py in this same delivery, which adds the
# new column, backfills it from your existing problem_category/service_tags/
# is_custom_category data, and drops the three old columns.
# ---------------------------------------------------------------------------
    
    
class Worker(Base):
    __tablename__ = "workers"


    id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    location: Mapped[WKBElement] = mapped_column(Geography(geometry_type='POINT', srid=4326), nullable=False)   
    category: Mapped[str] = mapped_column(String, index=True, nullable=False) # this is the worker's main trade category,   
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), index=True, nullable=False) # this is a list of specific skills or services   
    years_experience: Mapped[int] = mapped_column(nullable=False)  # this is the total years of experience the worker has in their trade
    additional_metadata: Mapped[dict] = mapped_column(JSONB, nullable=True)  # put extra info that can be use for future
    operating_radius: Mapped[float] = mapped_column(nullable=False) # this is the maximum distance in kilometers that the worker is willing to travel for a job
    
    


class JobStatus(str, enum.Enum):
    OPEN = "open"
    MATCHED = "matched"
    COMPLETED = "completed"
    
 
class Service_tasks(Base):
    __tablename__ = "service_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    problem_description: Mapped[str] = mapped_column(Text, nullable=False) 
    image_url: Mapped[str] = mapped_column(String, nullable=True)
    location: Mapped[WKBElement] = mapped_column(Geography(geometry_type='POINT', srid=4326), nullable=False)
    ai_extracted_json: Mapped[dict] = mapped_column(JSONB, nullable=True)
    status: Mapped[JobStatus] = mapped_column(
    Enum(JobStatus, name="job_status_enum"), 
    nullable=False, 
    default=JobStatus.OPEN # Python handles the default assignment smoothly
)
    
    
class Chat_logs(Base):
    __tablename__ = "chat_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("service_tasks.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_context: Mapped[str] = mapped_column(String, nullable=False) 
    message_body: Mapped[str] = mapped_column(Text, nullable=False) 
    sender: Mapped[str] = mapped_column(String, nullable=False) 
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default="now()")
    
    

class BidStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    SELECTED = "selected"
    REJECTED = "rejected"


class Bids(Base):
    __tablename__ = "bids"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("service_tasks.id", ondelete="CASCADE"), nullable=False)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True) 
    status: Mapped[BidStatus] = mapped_column(
    Enum(BidStatus, name="bid_status_enum"), 
    nullable=False, 
    default=BidStatus.SUBMITTED # Python handles the default assignment smoothly
)
    
    
    
class WorkerSkillsSchema(BaseModel):
    primary_trades: List[str] = Field(default_factory=list, description="Main categories like Plumbing, Electrical, Carpentry, HVAC")
    specific_skills: List[str] = Field(default_factory=list, description="Specific tasks they can do, e.g., fixing leaks, installing ceiling fans, drywall patching")
    years_of_experience: int = Field(default=0, description="Total years of experience as an integer")
    special_tools: List[str] = Field(default_factory=list, description="Key tools they own, e.g., ladders, power drills, welding gear, snakes")
    certifications: List[str] = Field(default_factory=list, description="Any professional licenses or certifications mentioned")
    estimated_hourly_rate: Optional[float] = Field(None, description="Their preferred hourly rate if mentioned, otherwise null")
    ai_confidence_summary: str = Field(default="", description="A brief paragraph summarizing their professional background and reliability based on the chat")




"""
New table needed in your model.py — worker interview pipeline
================================================================
This is a NEW table, not a modification of booking_chats. A worker
registration interview has its own lifecycle (interview -> scenario test
-> pass/reject -> profile) that doesn't fit the customer BookingChat shape,
so it gets its own model.

Required import in your model.py, if not already present:
  from sqlalchemy.dialects.postgresql import JSONB

Apply this as a diff against your real model.py — this isn't a full file
since I don't have your imports, Base class, or the rest of your models'
neighbors.
"""


class WorkerInterviewSession(Base):  # (Base) — keep your existing base class
    __tablename__ = "worker_interview_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    history: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)

    # State machine — see worker_interview_nvidia.py module docstring and
    # worker_interview_router.py.
    #   "interviewing"             -> normal Q&A, no test triggered yet
    #   "awaiting_scenario_answer" -> a scenario question has been asked;
    #                                  the worker's NEXT message is graded,
    #                                  not treated as an ordinary chat turn
    #   "complete"                 -> is_complete=True; check is_rejected
    #                                  to see which way it resolved
    stage: Mapped[str]= mapped_column(String, server_default="interviewing", nullable=False)

    is_complete: Mapped[bool]= mapped_column(Boolean, server_default="FALSE", nullable=False)
    is_rejected: Mapped[bool] = mapped_column(Boolean, server_default="FALSE", nullable=False)
    rejection_reason: Mapped[str | None]# = mapped_column(Text, nullable=True)

    # Set the moment [TEST_REQUIRED: ...] fires. Kept (not cleared) after
    # grading, so both the extraction step and the audit trail have it
    # without re-parsing the raw history.
    pending_sub_skill: Mapped[str | None]= mapped_column(Text, nullable=True)
    pending_scenario: Mapped[str | None]= mapped_column(Text, nullable=True)
    has_verified_specialty: Mapped[bool | None]= mapped_column(Boolean, nullable=True)

    scenario_score: Mapped[int | None]= mapped_column(Integer, nullable=True)
    scenario_passed: Mapped[bool | None]= mapped_column(Boolean, nullable=True)

    # Full validated WorkerProfileSchema, only populated on a genuine pass
    # where extraction also succeeded (see worker_interview_router.py's
    # _handle_scenario_answer for the pass-but-extraction-failed case).
    profile: Mapped[dict | None]= mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime]= mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime]= mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# ---------------------------------------------------------------------------
# Actual SQLAlchemy column definitions to copy in (same types you already
# use elsewhere in this file — JSONB import added):
# ---------------------------------------------------------------------------
#
#   from typing import Optional
#   from datetime import datetime
#   from sqlalchemy import String, Boolean, Text, Integer, DateTime, ForeignKey, func
#   from sqlalchemy.dialects.postgresql import JSONB
#   from sqlalchemy.orm import Mapped, mapped_column
#
#   class WorkerInterviewSession(Base):
#       __tablename__ = "worker_interview_sessions"
#
#       id: Mapped[int] = mapped_column(primary_key=True, index=True)
#       user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
#       history: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
#       stage: Mapped[str] = mapped_column(String, server_default="interviewing", nullable=False)
#       is_complete: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
#       is_rejected: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
#       rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
#       pending_sub_skill: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
#       pending_scenario: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
#       has_verified_specialty: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
#       scenario_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
#       scenario_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
#       profile: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
#       created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
#       updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
#
# Then generate + apply the matching Alembic migration — see
# alembic_migration_worker_interview.py in this same delivery, which
# creates the table from scratch (no backfill needed, since this table
# doesn't exist yet).
# ---------------------------------------------------------------------------