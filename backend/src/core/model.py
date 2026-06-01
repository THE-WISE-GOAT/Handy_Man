# This file defines the database schema for the User model using SQLAlchemy. This is use for components of database components

from typing import List
import uuid

from src.database.database import Base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, Text
from sqlalchemy.sql.sqltypes import TIMESTAMP, UUID, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum
from datetime import datetime
from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
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


class Worker(Base):
    __tablename__ = "workers"
    
    id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    location: Mapped[WKBElement] = mapped_column(Geography(geometry_type='POINT', srid=4326), nullable=False)
    ai_accessed_skills_json: Mapped[dict] = mapped_column(JSONB, nullable=True)


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
        server_default=JobStatus.OPEN.value
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
        server_default=BidStatus.SUBMITTED.value
    )