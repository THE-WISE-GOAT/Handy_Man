from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from src.core.manager import manager
from src.core.oauth2 import verify_access_token

router = APIRouter(tags=["WebSocket"])

@router.websocket("/ws/worker/{worker_chat_id}")
async def worker_websocket_endpoint(
    websocket: WebSocket, 
    worker_chat_id: int, 
    token: str
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials"
    )
    token_data = verify_access_token(token, credentials_exception)
    
    if int(token_data.id) != worker_chat_id: 
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect_worker(websocket, worker_chat_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_worker(worker_chat_id)


@router.websocket("/ws/booking/{booking_chat_id}")
async def customer_websocket_endpoint(
    websocket: WebSocket, 
    booking_chat_id: int, 
    token: str
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials"
    )
    token_data = verify_access_token(token, credentials_exception)
    
    # Optional: Safety check to ensure token_data.id owns this booking_chat_id
    # You might need a DB call here if you want strict validation, 
    # but for now, we'll establish the connection.

    await manager.connect_customer(websocket, booking_chat_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_customer(booking_chat_id)