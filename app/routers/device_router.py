from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session
from app.database import SessionLocal
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
    user_id: int
    device_type: Optional[str] = None
    os_version: Optional[str] = None
    device_token: Optional[str] = None
    output_audio_mode: Optional[str] = None
    preferred_delivery_mode: Optional[str] = None

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

@router.post("/update-device")
async def update_device(
    payload: DeviceUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    # Validate token matches user
    ensure_token_user_match(user_data["sub"], payload.user_id)

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.device_type = payload.device_type
    user.os_version = payload.os_version
    user.output_audio_mode = payload.output_audio_mode
    user.preferred_delivery_mode = payload.preferred_delivery_mode
    user.device_token = payload.device_token
    user.last_active_at = datetime.utcnow()

    db.commit()
    return {"message": "Device context updated successfully"}
