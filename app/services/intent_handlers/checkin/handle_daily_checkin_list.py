from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from app.models.daily_checkin import DailyCheckin
from app.models.user import User
from app.utils.auth_utils import ensure_token_user_match
from datetime import datetime

async def handle_checkin_list(request: Request, db: Session, user: User, intent_payload: dict):
    try:
        await ensure_token_user_match(request, user.id)

        checkins = db.query(DailyCheckin).filter(
            DailyCheckin.user_id == user.id
        ).order_by(DailyCheckin.date.desc()).limit(30).all()

        results = []
        for c in checkins:
            results.append({
                "id": c.id,
                "date": c.date.strftime("%Y-%m-%d"),
                "mood_rating": c.mood_rating,
                "gratitude": c.gratitude,
                "thoughts": c.thoughts,
                "emotion_label": c.emotion_label,
                "voice_summary": c.voice_summary,
            })

        return {
            "status": "success",
            "message": "Recent check-ins with emotion labels",
            "data": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving check-ins: {str(e)}")
