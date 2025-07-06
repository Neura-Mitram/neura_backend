# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.message_model import Message
from app.models.user import User
from app.utils.auth_utils import ensure_token_user_match, require_token, get_memory_messages
from app.utils.rate_limit_utils import get_tier_limit, limiter
from pydantic import BaseModel

router = APIRouter(prefix="/memory", tags=["Memory"])

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 🎯 Export
@router.get("/export")
@limiter.limit(get_tier_limit)
def export_memory(
    device_id: str = Query(..., description="The device_id assigned during anonymous login"),
    conversation_id: int = Query(1),
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], device_id)

    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found for this device_id")

    messages = (
        db.query(Message)
        .filter_by(user_id=user.id, conversation_id=conversation_id)
        .order_by(Message.timestamp)
        .all()
    )

    return [
        {
            "sender": m.sender,
            "message": m.message,
            "timestamp": m.timestamp.isoformat(),
            "important": m.important
        }
        for m in messages
    ]

# 🎯 Delete
@router.delete("/delete")
@limiter.limit(get_tier_limit)
def delete_memory(
    request: Request,
    device_id: str = Query(..., description="The device_id assigned during anonymous login"),
    conversation_id: int = 1,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], device_id)

    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found for this device_id")

    deleted = (
        db.query(Message)
        .filter_by(user_id=user.id, conversation_id=conversation_id)
        .delete()
    )
    db.commit()

    return {"deleted": deleted}



class MemoryLogRequest(BaseModel):
    device_id: str
    conversation_id: int = 1
    limit: int = 10
    offset: int = 0

@router.post("/memory-log")
@limiter.limit(get_tier_limit)
def get_memory_log(
    request: Request,
    payload: MemoryLogRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.device_id)

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.memory_enabled:
        return {"message": "Memory is disabled for this user."}

    messages = get_memory_messages(db, user.id, payload.limit, offset=payload.offset, conversation_id=payload.conversation_id)

    return {
        "memory_enabled": user.memory_enabled,
        "conversation_id": payload.conversation_id,
        "messages": [
            {
                "sender": msg.sender,
                "message": msg.message,
                "timestamp": msg.timestamp.isoformat(),
                "important": msg.important
            } for msg in messages
        ]
    }
