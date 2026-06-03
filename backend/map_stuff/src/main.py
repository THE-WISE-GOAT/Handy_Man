import os
from typing import List, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncpg

# Initialize API instance with custom configuration metadata
app_config = {"title": "Handyman Matching Engine"}
app = FastAPI(**app_config)

# CORS configuration allowing explicit resource sharing for web applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Extract infrastructure coordinates from environment space 
# Default string points to local sandbox database cluster
TARGET_DB_URI = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:password@localhost:5432/handyman_db"
)

# Incoming Pydantic payload interface definition
class JobCreate(BaseModel):
    title: str
    tag: str
    latitude: float
    longitude: float


@app.get("/")
async def get_server_health() -> Dict[str, str]:
    """Simple status check route to verify engine execution."""
    return {"status": "Server running successfully"}


@app.post("/api/jobs/match")
async def match_job(job: JobCreate) -> Dict[str, Any]:
    """
    Executes a high-velocity spatial query against the worker index.
    Matches availability across category tags and geographic radius bounds.
    """
    # Establish single-use network connection to target database cluster
    db_connection = await asyncpg.connect(TARGET_DB_URI)
    
    try:
        # Optimized spatial calculation tracking intersecting geometries
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
        
        # Transmit query parameters through database wire protocol
        query_records = await db_connection.fetch(
            geospatial_matching_sql, 
            job.tag, 
            job.longitude, 
            job.latitude
        )
        
        # Serialize database row metrics into a standardized list structure
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
        # Guarantee connection lifecycle termination to prevent socket leak
        await db_connection.close()