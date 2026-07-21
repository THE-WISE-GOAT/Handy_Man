# from fastapi import WebSocket
# from typing import Dict

# class ConnectionManager:
#     def __init__(self):
#         # Maps worker_chat_id -> WebSocket connection
#         self.active_connections: Dict[int, WebSocket] = {}

#     async def connect(self, worker_chat_id: int, websocket: WebSocket):
#         await websocket.accept()
#         self.active_connections[worker_chat_id] = websocket

#     def disconnect(self, worker_chat_id: int):
#         if worker_chat_id in self.active_connections:
#             del self.active_connections[worker_chat_id]

#     async def send_job_notification(self, worker_chat_id: int, job_data: dict):
#         if worker_chat_id in self.active_connections:
#             await self.active_connections[worker_chat_id].send_json({
#                 "type": "NEW_JOB_NOTIFICATION",
#                 "data": job_data
#             })

# # Global instance to be imported across the app
# manager = ConnectionManager()