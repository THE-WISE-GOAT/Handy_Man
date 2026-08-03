from fastapi import WebSocket
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Two separate pools to prevent ID collisions
        self.worker_connections: Dict[int, WebSocket] = {}
        self.customer_connections: Dict[int, WebSocket] = {}

    # --- WORKER METHODS ---
    async def connect_worker(self, websocket: WebSocket, worker_chat_id: int):
        await websocket.accept()
        self.worker_connections[worker_chat_id] = websocket

    def disconnect_worker(self, worker_chat_id: int):
        self.worker_connections.pop(worker_chat_id, None)

    async def send_worker_notification(self, worker_chat_id: int, message: dict):
        if worker_chat_id in self.worker_connections:
            websocket = self.worker_connections[worker_chat_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(
                    f"Error sending notification to worker {worker_chat_id}: {e}"
                )
                self.disconnect_worker(worker_chat_id)

    # --- CUSTOMER METHODS ---
    async def connect_customer(self, websocket: WebSocket, booking_chat_id: int):
        await websocket.accept()
        self.customer_connections[booking_chat_id] = websocket

    def disconnect_customer(self, booking_chat_id: int):
        self.customer_connections.pop(booking_chat_id, None)

    async def send_customer_notification(self, booking_chat_id: int, message: dict):
        if booking_chat_id in self.customer_connections:
            websocket = self.customer_connections[booking_chat_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(
                    f"Error sending notification to customer {booking_chat_id}: {e}"
                )
                self.disconnect_customer(booking_chat_id)


# Create a global instance to be used across your app
manager = ConnectionManager()
