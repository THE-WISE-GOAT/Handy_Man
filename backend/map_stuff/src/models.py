from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.dialects.postgresql import ARRAY 
from geoalchemy2 import Geography
from backend.map_stuff.src.database import Base

class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    operating_radius = Column(Float, nullable=False)
    tags = Column(ARRAY(String), nullable=False)
    location = Column(Geography(geometry_type='POINT', srid=4326, spatial_index=True), nullable=False)