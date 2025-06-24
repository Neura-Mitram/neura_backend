from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.daily_checkin_model import DailyCheckin
from app.utils.audio_processor import transcribe_audio
from app.utils.ai_engine import generate_ai_reply
from app.utils.auth_utils import ensure_token_user_match, require_token
import datetime
from pydantic import BaseModel
from typing import Optional
import uuid

from app.utils.rate_limit_utils import get_tier_limit, limiter

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class CheckinRequest(BaseModel):
    user_id: int
    mood_rating: int
    gratitude: str
    thoughts: str

@limiter.limit(get_tier_limit)
@router.post("/neura/daily-checkin")
async def daily_checkin(
    payload: CheckinRequest,
    voice_note: UploadFile = File(None),
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    # ✅ Verify user_id matches token
    ensure_token_user_match(user_data["sub"], payload.user_id)

    voice_summary = None
    if voice_note:
        filename = f"{uuid.uuid4()}.mp3"
        temp_path = f"/data/temp_audio/{filename}"
        with open(temp_path, "wb") as f:
            f.write(await voice_note.read())

        transcript = transcribe_audio(temp_path)
        prompt = f"Summarize this voice note in 3-4 sentences:\n{transcript}"
        voice_summary = generate_ai_reply(prompt)

    checkin = DailyCheckin(
        user_id=payload.user_id,
        date=datetime.date.today().isoformat(),
        mood_rating=payload.mood_rating,
        gratitude=payload.gratitude,
        thoughts=payload.thoughts,
        voice_summary=voice_summary
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)

    return {"message": "Check-in recorded", "checkin": checkin.id}

class ReflectionRequest(BaseModel):
    user_id: int

@limiter.limit(get_tier_limit)
@router.post("/neura/get-daily-checkin")
def get_checkins(payload: ReflectionRequest, db: Session = Depends(get_db), user_data: dict = Depends(require_token)):

    # ✅ Verify user_id matches token
    ensure_token_user_match(user_data["sub"], payload.user_id)

    records = (
        db.query(DailyCheckin)
        .filter_by(user_id=payload.user_id)
        .order_by(DailyCheckin.date.desc())
        .all()
    )

    return records

