# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.notification import NotificationLog
from app.models.user import User
from app.utils.auth_utils import require_token, ensure_token_user_match
from datetime import datetime

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# DB dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/recent")
def get_recent_notifications(
    device_id: str,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token),
    limit: int = 10
):
    ensure_token_user_match(user_data["sub"], device_id)

    # Get user from device ID
    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    logs = (
        db.query(NotificationLog)
        .filter(NotificationLog.user_id == user.id)
        .order_by(NotificationLog.timestamp.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": log.id,
            "type": log.notification_type,
            "text": log.content,  # Already decrypted automatically
            "delivered": log.delivered,
            "timestamp": log.timestamp.isoformat()
        }
        for log in logs
    ]


@router.patch("/mark-delivered/{notification_id}")
def mark_as_delivered(notification_id: int, db: Session = Depends(get_db)):
    log = db.query(NotificationLog).filter(NotificationLog.id == notification_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Notification not found")
    log.delivered = True
    db.commit()
    return {"status": "updated"}
