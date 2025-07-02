from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.message_model import Message
from app.models.user import User
from app.utils.auth_utils import require_token, ensure_token_user_match
from app.utils.rate_limit_utils import get_tier_limit, limiter

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
    user_id: int,
    conversation_id: int = 1,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], user_id)

    messages = (
        db.query(Message)
        .filter_by(user_id=user_id, conversation_id=conversation_id)
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
    user_id: int,
    conversation_id: int = 1,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], user_id)

    deleted = (
        db.query(Message)
        .filter_by(user_id=user_id, conversation_id=conversation_id)
        .delete()
    )
    db.commit()

    return {"deleted": deleted}
