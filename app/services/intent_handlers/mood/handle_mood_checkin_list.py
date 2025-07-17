# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import Request
from sqlalchemy.orm import Session
from app.models.mood import MoodLog
from app.models.user import User

async def handle_mood_checkin_list(request: Request, user: User, message: str, db: Session):
    logs = (
        db.query(MoodLog)
        .filter(MoodLog.user_id == user.id)
        .order_by(MoodLog.timestamp.desc())
        .limit(30)
        .all()
    )

    result = []
    for log in logs:
        result.append({
            "mood": log.mood_rating,
            "energy": log.energy_level,
            "note": log.note,
            "emotion": log.emotion_tone,
            "time": log.timestamp.strftime("%b %d, %I:%M %p")
        })

    return {
        "type": "mood_history",
        "logs": result
    }
