from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.database.database import get_db

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"]
)

@router.get("/my-tasks")
def get_customer_tasks(db: Session = Depends(get_db)):
    try:
        # 1. Look up active user in current session matrix
        customer_id = 2

        # 2. Fetch tasks matching this customer_id
        tasks_query = text("""
            SELECT id, problem_description 
            FROM service_tasks 
            WHERE customer_id = :customer_id 
            ORDER BY id DESC;
        """)
        results = db.execute(tasks_query, {"customer_id": customer_id}).fetchall()

        # 3. Format into structured list
        tasks_list = [
            {"id": row[0], "problem_description": row[1]} 
            for row in results
        ]
        return {"status": "success", "tasks": tasks_list}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))