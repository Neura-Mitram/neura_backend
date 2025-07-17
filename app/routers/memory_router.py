# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.message_model import Message
from app.models.user import User
from app.utils.auth_utils import ensure_token_user_match, require_token
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
def export_user_memory(
    device_id: str = Query(..., description="The device_id assigned during anonymous login"),
    conversation_id: int = Query(1),
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], device_id)

    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found for this device_id")

    if not user.memory_enabled:
        return {"message": "Memory is disabled for this user."}

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
            "important": m.important,
            "emotion_label": m.emotion_label
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

    if not user.memory_enabled:
        return {"message": "Memory is disabled for this user."}

    deleted = (
        db.query(Message)
        .filter_by(user_id=user.id, conversation_id=conversation_id)
        .delete()
    )
    db.commit()

    return {"deleted": deleted}


# 📥 Memory Log Request
class MemoryLogRequest(BaseModel):
    device_id: str
    conversation_id: int = 1
    limit: int = 10
    offset: int = 0
    important_only: bool = False  # ✅ Optional filter
    emotion_filter: str = None

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

    messages = get_memory_messages(
        db,
        user.id,
        payload.limit,
        offset=payload.offset,
        conversation_id=payload.conversation_id,
        important_only=payload.important_only,
        emotion_filter=payload.emotion_filter
    )

    return {
        "memory_enabled": user.memory_enabled,
        "conversation_id": payload.conversation_id,
        "messages": [
            {
                "sender": msg.sender,
                "message": msg.message,
                "timestamp": msg.timestamp.isoformat(),
                "important": msg.important,
                "emotion_label": msg.emotion_label
            } for msg in messages
        ]
    }

# 🌟 Mark Important
class MarkImportantRequest(BaseModel):
    device_id: str
    message_id: int
    important: bool

@router.post("/mark-important")
@limiter.limit(get_tier_limit)
def mark_important_message(
    payload: MarkImportantRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.device_id)

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    message = db.query(Message).filter(
        Message.user_id == user.id,
        Message.id == payload.message_id
    ).first()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    message.important = payload.important
    db.commit()

    return {
        "message_id": message.id,
        "important": message.important,
        "status": "updated"
    }


# 📤 Utility to get filtered messages
# ✅ Get memory messages for /memory-log with optional important_only
def get_memory_messages(
    db: Session,
    user_id: int,
    limit: int = 10,
    offset: int = 0,
    conversation_id: int = 1,
    important_only: bool = False,
    emotion_filter: str = None
):
    query = (
        db.query(Message)
        .filter(Message.user_id == user_id)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp.desc())
    )

    if important_only:
        query = query.filter(Message.important.is_(True))

    msgs = query.offset(offset).limit(limit).all()
    msgs.reverse()
    return msgs