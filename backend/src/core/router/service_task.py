from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.database.database import get_db

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