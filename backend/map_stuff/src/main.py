import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import JobCreate
from .database import get_db  

app_config = {"title": "Handyman Matching Engine"}
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

    geospatial_matching_sql = text("""
        SELECT w.user_id, w.radius
        FROM workers w
        WHERE :tag = ANY(w.tags)
          AND ST_DWithin(
            w.location, 
            ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography, 
            w.radius
          );
    """)
    
    query_result = await db.execute(
        geospatial_matching_sql, 
        {
            "tag": job.tag, 
            "longitude": job.longitude, 
            "latitude": job.latitude
        }
    )
    
    formatted_matches = [
        {
            "worker_id": row.user_id, 
            "radius": row.radius
        }
        for row in query_result.all()
    ]
    
    return {
        "status": "success",
        "total_matches": len(formatted_matches),
        "matches": formatted_matches
    }