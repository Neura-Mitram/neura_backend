# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.user import User
from app.models.habit import Habit
from app.utils.ai_engine import generate_ai_reply
from app.utils.auth_utils import ensure_token_user_match
from fastapi import HTTPException, Request
import json
from app.services.emotion_tone_updater import update_emotion_status
from datetime import datetime, timedelta
from app.utils.prompt_templates import habit_modify_prompt
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.usage_tracker import track_usage_event

async def handle_modify_habit(request: Request, user: User, message: str, db: Session):
    # Ensure token-user match
    # await ensure_token_user_match(request, user.id)

    # 🔍 Emotion Detection
    emotion_label = await update_emotion_status(user, message, db, source="habit_modify")

    """
    Uses Mistral to extract habit_id and updated values (name/frequency).
    """
    prompt = habit_modify_prompt(message, emotion_label)

    try:
        response = json.loads(generate_ai_reply(inject_persona_into_prompt(user, prompt, db)))

        data = response
        habit = db.query(Habit).filter(Habit.id == data["habit_id"]).first()
        if not habit or habit.user_id != user.id:
            raise HTTPException(status_code=404, detail="Habit not found or unauthorized")

        habit.habit_name = data["habit_name"]
        habit.frequency = data["frequency"]
        habit.emotion_label = emotion_label
        db.commit()
        db.refresh(habit)
        track_usage_event(db, user, category="habit_modify")

        return {"message": "✅ Habit updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"🛑 Failed to modify habit: {e}")