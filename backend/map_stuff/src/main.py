import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import asyncpg

app = FastAPI(title="Handyman Matching Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows any origin (including localhost:5173)
    allow_credentials=True,
    allow_methods=["*"],  # Allows POST, GET, OPTIONS, etc.
    allow_headers=["*"],
)

# GIT-SAFE DATABASE CONFIGURATION
# Looks for DATABASE_URL in your system environment variables. 
# Falls back to local sandbox configuration if not found.
DB_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:password@localhost:5432/handyman_db"
)

# Data schemas incoming from React
class JobCreate(BaseModel):
    title: str
    tag: str
    latitude: float
    longitude: float

@app.get("/")
async def root():
    return {"status": "Server running successfully"}

@app.post("/api/jobs/match")
async def match_job(job: JobCreate):
    # 1. Open a lightning-fast async connection to your local database
    conn = await asyncpg.connect(DB_URL)
    
    try:
        # 2. THE REAL POSTGIS MATCHING QUERY
        # Finds workers who have the skill AND whose radius covers this job site
        query = """
            SELECT w.user_id, w.radius
            FROM workers w
            WHERE $1 = ANY(w.tags)
              AND ST_DWithin(
                w.location, 
                ST_SetSRID(ST_MakePoint($2, $3), 4326)::geography, 
                w.radius
              );
        """
        
        matched_workers = await conn.fetch(query, job.tag, job.longitude, job.latitude)
        
        # 3. Format the results cleanly into a list of dictionaries
        results = [
            {"worker_id": row["user_id"], "radius": row["radius"]} 
            for row in matched_workers
        ]
        
        return {
            "status": "success",
            "total_matches": len(results),
            "matches": results
        }
        
    finally:
        # Always close the connection when done!
        await conn.close()