# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.



from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel
from app.models.database import SessionLocal
from app.models.user import User
from app.utils.auth_utils import require_token, ensure_token_user_match
from app.utils.tier_logic import is_in_private_mode, get_private_mode_duration_minutes

router = APIRouter(prefix="/neura-pm", tags=["Private Mode"])
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# For Private Mode (DND Active)
class PrivateModeInput(BaseModel):
    device_id: str
    enable: bool  # true = go private, false = turn off

@router.post("/private-mode")
async def toggle_private_mode(
    payload: PrivateModeInput,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.device_id)

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_private = payload.enable
    user.last_private_on = datetime.utcnow() if payload.enable else None
    db.commit()

    print(f"🔕 Private mode {'enabled' if payload.enable else 'disabled'} for {user.temp_uid}")
    return {
        "status": "updated",
        "is_private": user.is_private
    }


@router.get("/private-mode-status")
def private_mode_status(
    device_id: str,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], device_id)
    user = db.query(User).filter(User.temp_uid == device_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if not user.is_private or not user.last_private_on:
        return {
            "is_private": False,
            "expired": True,
            "time_remaining": 0
        }

    max_duration = get_private_mode_duration_minutes(user)
    elapsed = (datetime.utcnow() - user.last_private_on).total_seconds() / 60
    remaining = int(max(0, max_duration - elapsed))
    expired = remaining <= 0

    return {
        "is_private": user.is_private,
        "last_private_on": user.last_private_on.isoformat(),
        "expired": expired,
        "time_remaining": remaining
    }