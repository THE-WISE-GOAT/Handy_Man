from fastapi import WebSocket
from typing import Dict

class ConnectionManager:
    def __init__(self):
        # Stores active connections: {worker_chat_id: WebSocket}
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, worker_chat_id: int):
        await websocket.accept()
        self.active_connections[worker_chat_id] = websocket

    def disconnect(self, worker_chat_id: int):
        if worker_chat_id in self.active_connections:
            del self.active_connections[worker_chat_id]

    async def send_job_notification(self, worker_chat_id: int, message: dict):
        """Sends a job notification to a specific worker."""
        if worker_chat_id in self.active_connections:
            websocket = self.active_connections[worker_chat_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"Error sending notification to {worker_chat_id}: {e}")
                self.disconnect(worker_chat_id)
        else:
            print(f"Worker {worker_chat_id} is not connected to WebSocket.")

# Create a global instance to be used across your app
manager = ConnectionManager()