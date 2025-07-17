# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.user import User
from app.models.daily_checkin import DailyCheckin
from app.utils.auth_utils import ensure_token_user_match
from app.services.emotion_tone_updater import update_emotion_status
from app.utils.ai_engine import generate_ai_reply
from fastapi import HTTPException, Request
from datetime import datetime
import json
from app.utils.prompt_templates import checkin_add_prompt
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.usage_tracker import track_usage_event

async def handle_checkin_add(request: Request, db: Session, user: User, intent_payload: dict):
    try:
        # await ensure_token_user_match(request, user.id)

        mood_rating = intent_payload.get("mood_rating")
        gratitude = intent_payload.get("gratitude", "")
        thoughts = intent_payload.get("thoughts", "")
        voice_note = intent_payload.get("voice_note", "")

        # 🔍 Step 1: Emotion Detection from thoughts
        emotion_label = await update_emotion_status(user, thoughts, db, source="checkin_add")

        # 🧠 Step 2: Generate AI insight based on tone and thoughts

        prompt = checkin_add_prompt(intent_payload, emotion_label)

        ai_response = generate_ai_reply(inject_persona_into_prompt(user, prompt, db))

        insight = json.loads(ai_response).get("ai_insight", "")

        # 📝 Step 3: Save check-in with emotion + optional voice + AI insight
        new_checkin = DailyCheckin(
            user_id=user.id,
            mood_rating=mood_rating,
            gratitude=gratitude,
            thoughts=thoughts,
            voice_summary=voice_note,
            emotion_label=emotion_label,
            ai_insight=insight,
            date=datetime.utcnow().date()
        )

        db.add(new_checkin)
        db.commit()
        db.refresh(new_checkin)
        track_usage_event(db, user, category="checkin_add")

        return {
            "status": "success",
            "message": f"Check-in saved with emotion '{emotion_label}'",
            "checkin_id": new_checkin.id,
            "ai_insight": insight
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in check-in: {str(e)}")
