from typing import List
from pydantic import BaseModel, Field

class JobCreate(BaseModel):
    """Payload received when a customer posts a task to find matching workers."""
    title: str = Field(..., description="Short summary of the task")
    problem_description: str = Field(..., description="Detailed explanation of the issue")
    tags: List[str] = Field(default_factory=list, description="Target skill categories needed e.g. ['plumber']")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class WorkerMatchResponse(BaseModel):
    """Details of an individual worker who qualifies for the job criteria."""
    worker_id: int
    operating_radius: float = Field(..., description="The worker's max travel limit")
    distance_miles: float = Field(..., description="Calculated live distance from the job location via PostGIS")
    
    class Config:
        from_attributes = True


class MatchResultResponse(BaseModel):
    """The master wrapper returned to the frontend showing all qualified service matches."""
    status: str = Field("success", description="Status message of the matching engine execution")
    total_matches: int
    matches: List[WorkerMatchResponse]

    class Config:
        from_attributes = True