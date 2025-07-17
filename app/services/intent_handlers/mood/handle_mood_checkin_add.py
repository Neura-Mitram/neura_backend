# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import Request
from sqlalchemy.orm import Session
from app.utils.auth_utils import generate_ai_reply
from app.models.mood import MoodLog
from app.models.user import User
from app.services.emotion_tone_updater import update_emotion_status
from datetime import datetime
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.usage_tracker import track_usage_event

async def handle_mood_checkin_add(request: Request, user: User, message: str, db: Session):
    # Placeholder for mood parsing — replace later via entities
    mood_rating = 6
    energy = 5
    note = message.strip()

    # Emotion detection
    emotion = await update_emotion_status(user, note, db, source="mood")

    # Motivational reply from AI
    prompt = f"A user rated their mood {mood_rating}/10 and energy {energy}. Their note: '{note}'. Give a short motivational response."
    ai_feedback = generate_ai_reply(inject_persona_into_prompt(user, prompt, db))

    # Save to DB
    mood_log = MoodLog(
        user_id=user.id,
        mood_rating=mood_rating,
        energy_level=energy,
        note=note,
        ai_feedback=ai_feedback,
        emotion_label=emotion,
        timestamp=datetime.utcnow()
    )
    db.add(mood_log)
    db.commit()
    db.refresh(mood_log)
    track_usage_event(db, user, category="mood_add")

    return {
        "type": "mood",
        "ai_feedback": ai_feedback,
        "emotion": emotion,
        "mood_rating": mood_rating
    }

