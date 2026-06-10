import os
from typing import List, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . schemas import JobCreate
import asyncpg

app_config = {"title": "Handyman Matching Engine"}
app = FastAPI(**app_config)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TARGET_DB_URI = os.getenv(
    "postgresql://postgres:password@localhost:5432/handyman_db"
)

@app.get("/")
async def get_server_health():
    return {"status": "Server running successfully"}


@app.post("/api/jobs/match")
async def match_job(job: JobCreate):
    
    db_connection = await asyncpg.connect(TARGET_DB_URI)
    
    try:
       
        geospatial_matching_sql = """
            SELECT w.user_id, w.radius
            FROM workers w
            WHERE $1 = ANY(w.tags)
              AND ST_DWithin(
                w.location, 
                ST_SetSRID(ST_MakePoint($2, $3), 4326)::geography, 
                w.radius
              );
        """
        
       
        query_records = await db_connection.fetch(
            geospatial_matching_sql, 
            job.tag, 
            job.longitude, 
            job.latitude
        )
        
      
        formatted_matches = [
            {
                "worker_id": record["user_id"], 
                "radius": record["radius"]
            }
            for record in query_records
        ]
        
        return {
            "status": "success",
            "total_matches": len(formatted_matches),
            "matches": formatted_matches
        }
        
    finally:
     
        await db_connection.close()