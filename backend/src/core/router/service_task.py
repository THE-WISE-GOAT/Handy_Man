# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.orm import Session
# from src.core import model, schema
# from src.database.database import get_db
# from src.core.oauth2 import get_current_user
# from typing import List

# router = APIRouter(
#     prefix="/service-tasks",
#     tags=["service_tasks"]
# )

# @router.post("/", status_code=status.HTTP_201_CREATED)
# def create_service_task(
#     problem_description: str,
#     location_lat: float,
#     location_lng: float,
#     db: Session = Depends(get_db),
#     current_user: model.User = Depends(get_current_user)
# ):
#     from geoalchemy2.elements import WKBElement
#     from geoalchemy2.shape import from_shape
#     from shapely.geometry import Point
    
#     point = Point(location_lng, location_lat)
#     location = from_shape(point, srid=4326)
    
#     task = model.Service_tasks(
#         customer_id=current_user.id,
#         problem_description=problem_description,
#         location=location
#     )
    
#     db.add(task)
#     db.commit()
#     db.refresh(task)
    
#     return {"task_id": task.id, "message": "Service task created successfully"}

# @router.get("/", status_code=status.HTTP_200_OK)
# def get_user_tasks(
#     db: Session = Depends(get_db),
#     current_user: model.User = Depends(get_current_user)
# ):
#     tasks = db.query(model.Service_tasks).filter(
#         model.Service_tasks.customer_id == current_user.id
#     ).order_by(model.Service_tasks.id.desc()).limit(50).all()
    
#     return tasks

# @router.get("/available-workers", status_code=status.HTTP_200_OK)
# def get_available_workers(
#     lat: float,
#     lng: float,
#     radius_km: float = 10.0,
#     db: Session = Depends(get_db),
#     current_user: model.User = Depends(get_current_user)
# ):
#     from sqlalchemy import func
#     from geoalchemy2.functions import ST_DistanceSphere
    
#     point = func.ST_Point(lng, lat, srid=4326)
    
#     workers = db.query(model.Worker).filter(
#         ST_DistanceSphere(model.Worker.location, point) <= radius_km * 1000
#     ).limit(20).all()
    
#     return [
#         {
#             "id": w.id,
#             "skills": w.ai_accessed_skills_json,
#             "operating_radius": w.operating_radius,
#             "tags": w.tags
#         }
#         for w in workers
#     ]

# @router.delete("/logout", status_code=status.HTTP_200_OK)
# def logout_session(
#     db: Session = Depends(get_db),
#     current_user: model.User = Depends(get_current_user)
# ):
#     return {"message": "Session terminated successfully"}