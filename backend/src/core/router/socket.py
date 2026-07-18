from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from src.core.manager import manager
from src.core.oauth2 import verify_access_token

router = APIRouter(tags=["WebSocket"])

@router.websocket("/ws/{worker_chat_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    worker_chat_id: int, 
    token: str
):
    # 1. Verify Token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials"
    )
    token_data = verify_access_token(token, credentials_exception)
    
    # 2. Safety check: ensure the authenticated user matches the requested worker_chat_id
    if int(token_data.id) != worker_chat_id: # Ensure 'id' matches the field in your token_data
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 3. Connect
    await manager.connect(websocket, worker_chat_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(worker_chat_id)