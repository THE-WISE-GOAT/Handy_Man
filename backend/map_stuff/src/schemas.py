from pydantic import BaseModel
from typing import List

class JobCreate(BaseModel):
    title: str
    tag: str
    latitude: float
    longitude: float

class WorkerMatchResponse(BaseModel):
    worker_id: int
    radius: int

class MatchResultResponse(BaseModel):
    status: str
    total_matches: int
    matches: List[WorkerMatchResponse]