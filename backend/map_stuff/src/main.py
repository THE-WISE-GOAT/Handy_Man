from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_DWithin

# Universal imports updated to match your latest structure
from .schemas import JobCreate, MatchResultResponse
from .database import get_db
from .models import Worker # This points to our modern Mapped Worker model

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


@app.post("/api/jobs/match", response_model=MatchResultResponse)
async def match_job(job: JobCreate, db: AsyncSession = Depends(get_db)):
    """
    Finds nearby matching handymen using modern SQLAlchemy ORM expressions
    and your structural matching schemas.
    """
    
    # 1. Standardize frontend decimal coordinates into a clear geometric coordinate point
    user_location = func.ST_SetSRID(
        func.ST_MakePoint(job.longitude, job.latitude), 
        4326
    )
    
    # 2. Build out the query constraints
    # Changed Worker.tags.contains to handle JSONB/Array matching natively depending on your DB layout.
    # We loop through job.tags (plural) to find array intersections.
    query = select(Worker.id, Worker.operating_radius).where(
        Worker.tags.has_any(job.tags), # Fast array/json search matrix intersection
        ST_DWithin(Worker.location, user_location, Worker.operating_radius)
    )
    
    # 3. Asynchronously execute the query pool using asyncpg
    query_result = await db.execute(query)
    
    # 4. Formulate dictionary mappings to align directly with your WorkerMatchResponse schema
    formatted_matches = [
        {
            "worker_id": row.id, 
            "operating_radius": row.operating_radius,
            # If you want real distance calculation from user_location, PostGIS can do it here!
        }
        for row in query_result.all()
    ]
    
    return {
        "status": "success",
        "total_matches": len(formatted_matches),
        "matches": formatted_matches
    }