# This file defines the database schema for the User model using SQLAlchemy. This is use for components of database components

from typing import List, Optional
from pydantic import BaseModel, Field
from src.database.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Boolean, ForeignKey, Enum, Text, ARRAY, Float, text
from sqlalchemy.sql.sqltypes import TIMESTAMP, UUID, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
import enum
from datetime import datetime
from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import JSON
from sqlalchemy import DateTime, JSON, func  
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from pgvector.sqlalchemy import Vector
from typing import Dict, Any

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    firstName: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lastName: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phonenumber: Mapped[Optional[str]] = mapped_column("phonenumber", String, nullable=True)
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



class BookingChat(Base): 
    __tablename__ = "booking_chats"
    
    id: Mapped[int]= mapped_column(primary_key=True, index=True)
    user_id: Mapped[int]= mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    history: Mapped[list[dict]] = mapped_column(JSON, default=list) # store chat history as a list of dictionaries
    is_complete: Mapped[bool]  = mapped_column(Boolean, server_default='FALSE', nullable=False) # tell if the chat is complete or not
    is_job_request: Mapped[bool]   = mapped_column(Boolean, server_default='FALSE', nullable=False) # tell if the chat is a job request or not
    categories: Mapped[list[dict]]   = mapped_column(JSONB, nullable=True) # tell about job categories, this is a list of dictionaries, each dictionary contains the category name and the subcategories
    problem_description: Mapped[str | None] = mapped_column(Text, nullable=True) # just text about the job request
    
    

# needs top work on it
class JobStatus(str, enum.Enum):
    OPEN = "open"
    MATCHED = "matched"
    COMPLETED = "completed"
    

# needs to work on it
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
    

# needs to work on it
class BidStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    SELECTED = "selected"
    REJECTED = "rejected"

# let's work on this later
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
    


#### models for the Worker Interview Session, this will be used to store the worker interview session data, including the chat history, the current stage of the interview, and the final outcome. 
class WorkerInterviewSession(Base):
    __tablename__ = "worker_interview_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    history: Mapped[list[dict]] = mapped_column(JSONB, nullable=False) # this will store the chat history as a list of dictionaries
    stage: Mapped[str]= mapped_column(String, server_default="interviewing", nullable=False) # what stage the interview is in, can be "interviewing", "completed", "rejected"
    is_complete: Mapped[bool]= mapped_column(Boolean, server_default="FALSE", nullable=False) # check if the interview is complete or not
    is_rejected: Mapped[bool] = mapped_column(Boolean, server_default="FALSE", nullable=False) # check if the interview is rejected or not
    rejection_reason: Mapped[str | None]= mapped_column(Text, nullable=True) # reason for rejection if applicable
    pending_sub_skill: Mapped[str | None]= mapped_column(Text, nullable=True) # this will store the sub skill that the worker is pending to complete
    pending_scenario: Mapped[str | None]= mapped_column(Text, nullable=True) # this will store the scenario that the worker will give test with this pending scenario
    has_verified_specialty: Mapped[bool | None]= mapped_column(Boolean, nullable=True) # after test they will be verifed
    scenario_score: Mapped[int | None]= mapped_column(Integer, nullable=True) # store score
    scenario_passed: Mapped[bool | None]= mapped_column(Boolean, nullable=True) # store passed or not
    # Optional link to the canonical WorkerProfile created after a successful interview
    worker_profile_id: Mapped[int | None] = mapped_column(ForeignKey("workers.id", ondelete="SET NULL"), nullable=True)
    worker_profile: Mapped["WorkerProfile"] = relationship("WorkerProfile", back_populates="interview_sessions", lazy="selectin")

    # Snapshot of profile data at interview time; keep small to avoid duplication
    profile: Mapped[dict | None]= mapped_column(JSONB, nullable=True) # this will store the final profile of the worker after the interview is complete
    created_at: Mapped[datetime]= mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False) # this will store the time when the interview session is created
    updated_at: Mapped[datetime]= mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False) # this will store the time when the interview session is updated




### model  for the Worker Profile, this will be used to store the worker profile data, including the skills, experience, and other relevant information. This will be used to match the worker with the job requests.
class WorkerProfile(Base):
    __tablename__ = "workers"

        # Core Identifiers
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    worker_chat_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    # Outer Metadata Fields
    stage: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "complete"
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_rejected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Nested Profile Content Fields
    job_category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # e.g., "plumber"
    category_tag: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "plumbing"
    is_custom_category: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Lists mapped to native PostgreSQL string arrays
    specialities: Mapped[list[str]] = mapped_column(ARRAY(String(100)), nullable=False, default=list)
    specialized_tools_or_equipment: Mapped[list[str]] = mapped_column(ARRAY(String(100)), nullable=False, default=list)
    # Text, Numerical, and License Fields
    years_experience: Mapped[int] = mapped_column(Integer, nullable=False)
    license_or_certification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    # Status, Flags, and Scores
    emergency_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_verified_specialty: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scenario_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scenario_score: Mapped[int] = mapped_column(Integer, nullable=False)
    # AI Vector Column (CRUCIAL!)
    # Stores the 4,096 numbers from nvidia/nv-embed-v1 generated from the 'job_description'
    description_vector: Mapped[list[float]] = mapped_column(Vector(4096), nullable=True)
    # Back-reference to interview sessions that produced or reference this profile
    interview_sessions: Mapped[List["WorkerInterviewSession"]] = relationship("WorkerInterviewSession", back_populates="worker_profile", lazy="selectin")
    
    
class CustomerChatData(Base):
    __tablename__ = "customer_chat_data"

    # Core Identifiers
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    booking_chat_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    
    # Outer Metadata Fields
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_job_request: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Text, Numerical, and Description Fields
    problem_description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Nested Profile Content Fields (Stored as a native PostgreSQL JSONB Array)
    # Stores: [{"category": str, "tags": [str], "is_custom_category": bool}, ...]
    categories: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    
    # AI Vector Column
    # Stores the 4,096 numbers from nvidia/nv-embed-v1 generated from 'problem_description'
    description_vector: Mapped[List[float]] = mapped_column(Vector(4096), nullable=True)