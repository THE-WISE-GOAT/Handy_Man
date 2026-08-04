from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    status,
    Depends,
)
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.core.manager import manager
from src.core.oauth2 import verify_access_token
from src.database.database import get_db
from src.core import model

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/worker/{worker_chat_id}")
async def worker_websocket_endpoint(
    websocket: WebSocket, worker_chat_id: int, token: str, db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        token_data = verify_access_token(token, credentials_exception)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    session_record = db.execute(
        select(model.WorkerInterviewSession).where(
            model.WorkerInterviewSession.id == worker_chat_id,
            model.WorkerInterviewSession.user_id == int(token_data.user_id),
        )
    ).scalar_one_or_none()

    if not session_record:
        worker_profile = db.execute(
            select(model.WorkerProfile).where(
                model.WorkerProfile.user_id == int(token_data.user_id)
            )
        ).scalar_one_or_none()

        if worker_profile:
            match_record = db.execute(
                select(model.JobWorkerMatch)
                .join(model.Job, model.JobWorkerMatch.job_id == model.Job.id)
                .where(
                    model.Job.booking_chat_id == worker_chat_id,
                    model.JobWorkerMatch.worker_id == worker_profile.id,
                    model.JobWorkerMatch.is_active == True,
                    model.JobWorkerMatch.is_rejected == False,
                )
            ).scalar_one_or_none()

            if not match_record:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
        else:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await manager.connect_worker(websocket, worker_chat_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_worker(worker_chat_id)


@router.websocket("/ws/{worker_chat_id}")
async def worker_websocket_endpoint_short(
    websocket: WebSocket,
    worker_chat_id: int,
    token: str,
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        token_data = verify_access_token(token, credentials_exception)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    session_record = db.execute(
        select(model.WorkerInterviewSession).where(
            model.WorkerInterviewSession.id == worker_chat_id,
            model.WorkerInterviewSession.user_id == int(token_data.user_id),
        )
    ).scalar_one_or_none()

    if not session_record:
        worker_profile = db.execute(
            select(model.WorkerProfile).where(
                model.WorkerProfile.user_id == int(token_data.user_id)
            )
        ).scalar_one_or_none()

        if worker_profile:
            match_record = db.execute(
                select(model.JobWorkerMatch)
                .join(model.Job, model.JobWorkerMatch.job_id == model.Job.id)
                .where(
                    model.Job.booking_chat_id == worker_chat_id,
                    model.JobWorkerMatch.worker_id == worker_profile.id,
                    model.JobWorkerMatch.is_active == True,
                    model.JobWorkerMatch.is_rejected == False,
                )
            ).scalar_one_or_none()

            if not match_record:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
        else:
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
    token: str,
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        token_data = verify_access_token(token, credentials_exception)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    booking_session = db.execute(
        select(model.BookingChat).where(
            model.BookingChat.id == booking_chat_id,
            model.BookingChat.user_id == int(token_data.user_id),
        )
    ).scalar_one_or_none()

    if not booking_session:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect_customer(websocket, booking_chat_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_customer(booking_chat_id)
