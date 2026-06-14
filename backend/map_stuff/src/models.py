from typing import List, Optional
from datetime import datetime
from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from backend.map_stuff.src.database import Base # Keeps your specific database import path

class Worker(Base):
    __tablename__ = "workers"
    
    # 1. Identity Link: Serves as Primary Key and Foreign Key pointing back to Users
    id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        primary_key=True, 
        index=True
    )
    
    # 2. Geospatial tracking: Notice 'spatial_index=True' is included inside the Geography type definition
    location: Mapped[WKBElement] = mapped_column(
        Geography(geometry_type='POINT', srid=4326, spatial_index=True), 
        nullable=False
    )
    
    # 3. Core Worker Characteristics
    operating_radius: Mapped[float] = mapped_column(nullable=False)
    tags: Mapped[List[str]] = mapped_column(JSONB, nullable=False) # Changed to JSONB or ARRAY(String) to match schema choice
    
    # 4. Structured AI Assessment Data
    ai_accessed_skills_json: Mapped[dict] = mapped_column(JSONB, nullable=True)
    
    # 5. The Python Memory Relationship (The navigation shortcut back to User)
    user: Mapped["User"] = relationship("User", back_populates="worker_profile")