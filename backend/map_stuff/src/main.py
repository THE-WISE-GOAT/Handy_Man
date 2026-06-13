from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_DWithin

# Import your clean schemas, managed database tools, and ORM blueprints
from .schemas import JobCreate
from .database import get_db
from .models import Worker

app_config = {"title": "kamigo"}
app = FastAPI(**app_config)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def get_server_health():
    return {"status": "Server running successfully"}


@app.post("/api/jobs/match")
async def match_job(job: JobCreate, db: AsyncSession = Depends(get_db)):
    """
    Finds nearby matching handymen using full SQLAlchemy ORM 
    instead of raw text-based SQL.
    """
    
    user_location = func.ST_SetSRID(
        func.ST_MakePoint(job.longitude, job.latitude), 
        4326
    )
    
    query = select(Worker.id, Worker.operating_radius).where(
        Worker.tags.contains([job.tag]),
        ST_DWithin(Worker.location, user_location, Worker.operating_radius)
    )
    
    query_result = await db.execute(query)
    
    formatted_matches = [
        {
            "id": row.id, 
            "operating_radius": row.operating_radius
        }
        for row in query_result.all()
    ]
    
    return {
        "status": "success",
        "total_matches": len(formatted_matches),
        "matches": formatted_matches
    }