# from fastapi import APIRouter, Depends
# from sqlalchemy.orm import Session
# from src.database.database import get_db
# from src.core import worker_table_manager
# from pydantic import BaseModel
# from typing import List

# router = APIRouter(prefix="/workers", tags=["Workers"])

# class WorkerLocationRequest(BaseModel):
#     worker_chat_ids: List[int]

# @router.post("/locations", summary="Get GPS locations for multiple matched workers")
# def get_worker_locations(payload: WorkerLocationRequest, db: Session = Depends(get_db)):
#     if not payload.worker_chat_ids:
#         return {"status": "success", "locations": []}
    
#     locations = worker_table_manager.get_workers_locations(db, payload.worker_chat_ids)
    
#     return {
#         "status": "success", 
#         "locations": locations
#     }