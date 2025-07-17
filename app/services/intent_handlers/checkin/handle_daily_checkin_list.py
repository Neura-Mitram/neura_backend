# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from app.models.daily_checkin import DailyCheckin
from app.models.user import User

async def handle_checkin_list(request: Request, db: Session, user: User, intent_payload: dict):
    try:
        # Optional emotion filter (e.g., "sad", "happy", etc.)
        emotion_filter = intent_payload.get("emotion")

        query = db.query(DailyCheckin).filter(DailyCheckin.user_id == user.id)
        if emotion_filter:
            query = query.filter(DailyCheckin.emotion_label == emotion_filter.lower())

        checkins = query.order_by(DailyCheckin.date.desc()).limit(30).all()

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
            "message": f"{'Filtered ' if emotion_filter else ''}check-ins returned",
            "data": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving check-ins: {str(e)}")
