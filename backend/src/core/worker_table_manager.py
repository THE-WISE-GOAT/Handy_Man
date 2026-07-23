# from sqlalchemy.orm import Session
# from sqlalchemy import select
# from src.core import model

# def get_workers_locations(db: Session, worker_chat_ids: list[int]):
#     """
#     Fetches the latitude and longitude for a given list of worker_chat_ids.
#     """
#     stmt = select(
#         model.WorkerProfile.worker_chat_id,
#         model.WorkerProfile.latitude,
#         model.WorkerProfile.longitude
#     ).where(
#         model.WorkerProfile.worker_chat_id.in_(worker_chat_ids),
#         model.WorkerProfile.latitude.isnot(None),
#         model.WorkerProfile.longitude.isnot(None)
#     )
    
#     results = db.execute(stmt).all()
    
#     # We default 'is_interested' to False here. 
#     # Later, you can join this with the 'Bids' table to accurately reflect active interest.
#     return [
#         {
#             "worker_chat_id": row.worker_chat_id,
#             "latitude": row.latitude,
#             "longitude": row.longitude,
#             "is_interested": False 
#         }
#         for row in results
#     ]