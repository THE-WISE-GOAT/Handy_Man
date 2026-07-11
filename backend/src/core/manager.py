from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, profession: str):
        await websocket.accept()
        profession_key = profession.lower().strip()
        if profession_key not in self.active_connections:
            self.active_connections[profession_key] = []
        self.active_connections[profession_key].append(websocket)
        print(f"🔌 Worker connected to live channel: [{profession_key}]")

    def disconnect(self, websocket: WebSocket, profession: str):
        profession_key = profession.lower().strip()
        if profession_key in self.active_connections:
            self.active_connections[profession_key].remove(websocket)
            if not self.active_connections[profession_key]:
                del self.active_connections[profession_key]
        print(f"🔌 Worker disconnected from channel: [{profession_key}]")
    
    async def broadcast_to_profession(self, profession: str, message: dict):
        profession_key = profession.lower().strip()
        if profession_key in self.active_connections:
            for connection in self.active_connections[profession_key]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

manager = ConnectionManager()