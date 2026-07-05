from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.database.database import get_db
from pydantic import BaseModel
from ..manager import manager

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"]
)

# TODO: format according to alchemy, remove hardcode(fetch with current session customer, ...), ...
@router.get("/my-tasks")
def get_customer_tasks(db: Session = Depends(get_db)):
    try:
        customer_id = 3

        tasks_query = text("""
            SELECT id, job_title, job_desc, professional 
            FROM jobs
            WHERE cust_id = :cid 
            ORDER BY id DESC;
        """)
        results = db.execute(tasks_query, {"cid": customer_id}).fetchall()

        tasks_list = [
            {"id": row[0], "title": row[1], "description": row[2], "professional": row[3]} 
            for row in results
        ]
        return {"status": "success", "tasks": tasks_list}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

class CreateJob(BaseModel):
    cust_id: int
    title: str
    description: str
    professional: str

@router.post("/post-job")
async def createJob(payload: CreateJob, db: Session = Depends(get_db)):
    try:
        # Added 'id' to the RETURNING clause so created[0] matches your response schema
        query = text("""
            INSERT INTO jobs (cust_id, job_title, job_desc, professional) 
            VALUES (:cus, :tit, :des, :pro)
            RETURNING id, cust_id, job_title, job_desc, professional;
        """)
        
        # FIXED: Changed db.db.execute to db.execute
        result = db.execute(query, {
            "cus": payload.cust_id,
            "tit": payload.title,
            "des": payload.description,
            "pro": payload.professional
        })

        db.commit()
        created = result.fetchone()
        await db.refresh(created)
        

        await manager.broadcast_to_profession(
            created[4], {
                "type": "new_job",
                "id": created[0],
                "cust_id": created[1],
                "title": created[2],
                "description": created[3],
                "professional" : created[4],
            }
        )
        # Indexes now match the RETURNING order exactly: 
        # 0=id, 1=cust_id, 2=job_title, 3=job_desc, 4=professional
        return {
            "status": "success",
            "job": { 
                "id": created[0],
                "cust_id": created[1],
                "title": created[2],
                "description": created[3],
                "professional": created[4]
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))