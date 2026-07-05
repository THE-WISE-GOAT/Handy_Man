from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# CHANGE: import your existing manager
from ..manager import manager

router = APIRouter()

@router.websocket("/ws/{profession}")
async def websocket_endpoint(websocket: WebSocket, profession: str):

    # CHANGE: register this websocket under its profession
    await manager.connect(websocket, profession)

    try:
        while True:
            # CHANGE:
            # We don't need messages from the worker yet.
            # This simply keeps the websocket alive.
            await websocket.receive_text()

    except WebSocketDisconnect:

        # CHANGE: remove worker from active_connections
        manager.disconnect(websocket, profession)