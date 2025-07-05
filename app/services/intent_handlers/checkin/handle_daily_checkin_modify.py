# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.user import User
from app.models.daily_checkin import DailyCheckin
from app.services.mistral_ai_service import get_mistral_reply
from fastapi import Request, HTTPException
from app.utils.auth_utils import ensure_token_user_match
from app.services.emotion_tone_updater import update_emotion_status
import json
from datetime import datetime
from app.utils.prompt_templates import checkin_modify_prompt


async def handle_checkin_modify(request: Request, user: User, message: str, db: Session):
    # ✅ Ensure secure match
    await ensure_token_user_match(request, user.id)

    # 🔍 Emotion Detection from message
    emotion_label = await update_emotion_status(user, message, db)

    # 🧠 Prompt Mistral to extract update fields
    prompt = checkin_modify_prompt(message, emotion_label)

    try:
        parsed = json.loads(get_mistral_reply(prompt))

        # 🔍 Locate check-in by ID or date
        checkin = None
        if parsed.get("checkin_id"):
            checkin = db.query(DailyCheckin).filter_by(id=parsed["checkin_id"], user_id=user.id).first()
        elif parsed.get("date"):
            checkin_date = datetime.strptime(parsed["date"], "%Y-%m-%d").date()
            checkin = db.query(DailyCheckin).filter_by(date=checkin_date, user_id=user.id).first()

        if not checkin:
            raise HTTPException(status_code=404, detail="Check-in not found")

        # 🧩 Apply updates if available
        if "mood_rating" in parsed:
            mood = parsed["mood_rating"]
            if not (1 <= mood <= 10):
                raise ValueError("Mood must be between 1–10")
            checkin.mood_rating = mood

        if "gratitude" in parsed:
            checkin.gratitude = parsed["gratitude"]

        if "thoughts" in parsed:
            checkin.thoughts = parsed["thoughts"]

        # 💾 Save updated emotion tone
        checkin.emotion_label = emotion_label

        db.commit()
        db.refresh(checkin)

        return {
            "message": f"✅ Check-in updated for {checkin.date.isoformat()}",
            "updated_emotion": emotion_label
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"🛑 Failed to modify check-in: {e}")
