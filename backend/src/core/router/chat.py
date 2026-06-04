from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.core import model
from src.database.database import get_db
from src.core.oauth2 import get_current_user
from typing import List
from src.core.schema import CustomerProblemSchema

router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

@router.post("/message", status_code=status.HTTP_200_OK)
async def send_chat_message(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user)
):
    message = payload.get("message", "")
    
    chat_log = model.Chat_logs(
        user_id=current_user.id,
        role_context="customer",
        message_body=message,
        sender="user"
    )
    
    db.add(chat_log)
    db.commit()
    
    return {
        "response": "Diagnostic logged. I have pinned appropriate categorization markers onto your tracking dashboard configuration panel."
    }

@router.get("/history", status_code=status.HTTP_200_OK)
def get_chat_history(
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user)
):
    logs = db.query(model.Chat_logs).filter(
        model.Chat_logs.user_id == current_user.id
    ).order_by(model.Chat_logs.timestamp.asc()).limit(100).all()
    
    return [
        {
            "id": log.id,
            "message": log.message_body,
            "sender": log.sender,
            "timestamp": log.timestamp.isoformat()
        }
        for log in logs
    ]