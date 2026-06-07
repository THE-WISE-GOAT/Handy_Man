from sqlalchemy import Column, Integer, String, ARRAY
from geoalchemy2 import Geography
from src.database import Base

class Worker(Base):
    __tablename__ = "workers"

    user_id = Column(Integer, primary_key=True, index=True)
    radius = Column(Integer, nullable=False)
    tags = Column(ARRAY(String), nullable=False)
    location = Column(Geography(geometry_type='POINT', srid=4326, spatial_index=True), nullable=False)