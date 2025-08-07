# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import APIRouter, Body, Depends, HTTPException, Request, Form, Header
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from typing import Optional
from datetime import datetime

from app.models.user import User
from app.utils.auth_utils import require_token, ensure_token_user_match

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class DeviceUpdateRequest(BaseModel):
    device_id: str
    device_type: Optional[str]
    os_version: Optional[str]
    device_token: Optional[str]
    output_audio_mode: Optional[str]
    preferred_delivery_mode: Optional[str]
    device_token: Optional[str]

    @validator('device_type', pre=True, always=True)
    def default_device_type(cls, v):
        return v.strip() if v and v.strip() else "unknown"

    @validator('os_version', pre=True, always=True)
    def default_os_version(cls, v):
        return v.strip() if v and v.strip() else ""

    @validator('output_audio_mode', pre=True, always=True)
    def default_output_audio_mode(cls, v):
        return v.strip() if v and v.strip() else "speaker"

    @validator('preferred_delivery_mode', pre=True, always=True)
    def default_delivery_mode(cls, v):
        return v.strip() if v and v.strip() else "text"


@router.post("/update-device-context")
async def update_device_context(
    request: Request,
    payload: DeviceUpdateRequest = Body(...),
    fcm_token: Optional[str] = Header(None, alias="X-FCM-Token"),
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.device_id)

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        user.device_type = payload.device_type
        user.os_version = payload.os_version
        user.output_audio_mode = payload.output_audio_mode
        user.preferred_delivery_mode = payload.preferred_delivery_mode
        user.device_token = payload.device_token
        user.last_active_at = datetime.utcnow()

        # Update FCM token if provided
        if fcm_token:
            user.fcm_token = fcm_token

        db.commit()
        return {"success": True, "message": "Device + FCM updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/retry-device-fcm")
def retry_fcm_token(
    token: str = Form(...),
    device_id: str = Form(...),
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], device_id)

    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.fcm_token = token
    db.commit()
    return {"success": True, "message": "FCM token updated"}
