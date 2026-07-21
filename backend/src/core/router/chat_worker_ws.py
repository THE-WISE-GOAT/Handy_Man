# from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
# from src.core.connection_manager import manager
# from src.core.oauth2 import verify_access_token
# from src.database.database import get_db

# router = APIRouter(tags=["WebSocket"])

# @router.websocket("/ws/{worker_chat_id}")
# async def websocket_endpoint(
#     websocket: WebSocket, 
#     worker_chat_id: int, 
#     token: str
# ):
#     # 1. Verify User (Reusing your auth logic)
#     credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
#     token_data = verify_access_token(token, credentials_exception)
    
#     # 2. Safety check: ensure worker matches the ID connecting
#     if int(token_data.user_id) != worker_chat_id:
#         await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
#         return

#     # 3. Connect
#     await manager.connect(worker_chat_id, websocket)
#     try:
#         while True:
#             # Keep the connection alive
#             await websocket.receive_text()
#     except WebSocketDisconnect:
#         manager.disconnect(worker_chat_id)