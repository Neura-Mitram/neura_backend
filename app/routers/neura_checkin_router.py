from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.daily_checkin_model import DailyCheckin
from app.utils.audio_processor import transcribe_audio
from app.utils.ai_engine import generate_ai_reply
import datetime

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/neura/daily-checkin")
async def daily_checkin(
    user_id: int = Form(...),
    mood_rating: int = Form(...),
    gratitude: str = Form(...),
    thoughts: str = Form(...),
    voice_note: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    voice_summary = None
    if voice_note:
        temp_path = f"temp_audio/{voice_note.filename}"
        with open(temp_path, "wb") as f:
            f.write(await voice_note.read())

        transcript = transcribe_audio(temp_path)
        prompt = f"Summarize this voice note in 3-4 sentences:\n{transcript}"
        voice_summary = generate_ai_reply(prompt)

    checkin = DailyCheckin(
        user_id=user_id,
        date=datetime.date.today().isoformat(),
        mood_rating=mood_rating,
        gratitude=gratitude,
        thoughts=thoughts,
        voice_summary=voice_summary
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    return {"message": "Check-in recorded", "checkin": checkin.id}

@router.get("/neura/daily-reflection/{user_id}")
def get_checkins(user_id: int, db: Session = Depends(get_db)):
    records = db.query(DailyCheckin).filter_by(user_id=user_id).all()
    return records
