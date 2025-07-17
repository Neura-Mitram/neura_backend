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
from datetime import datetime
from app.services.emotion_tone_updater import update_emotion_status
from app.utils.prompt_templates import habit_add_prompt
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.usage_tracker import track_usage_event

async def handle_add_habit(request: Request, user: User, message: str, db: Session):
    # Ensure token-user match
    # await ensure_token_user_match(request, user.id)

    # 🔍 Emotion Detection
    emotion_label = await update_emotion_status(user, message, db, source="habit_add")

    """
    Uses Mistral to extract habit name and frequency from message,
    then creates a new HabitEntry with streak = 0.
    """
    prompt = habit_add_prompt(message, emotion_label)

    mistral_response = generate_ai_reply(inject_persona_into_prompt(user, prompt, db))

    try:
        parsed = json.loads(mistral_response)
        habit_name = parsed["habit_name"]
        frequency = parsed["frequency"]

        if frequency not in ["daily", "weekly", "monthly"]:
            raise ValueError("Invalid frequency")

        habit = Habit(
            user_id=user.id,
            habit_name=habit_name,
            frequency=frequency,
            streak=0,
            last_completed=None,
            motivation_tip=None,  # could be generated later
            emotion_label=emotion_label
        )
        db.add(habit)
        db.commit()
        db.refresh(habit)
        track_usage_event(db, user, category="habit_add")

        return {
            "message": "✅ New habit added",
            "habit": {
                "id": habit.id,
                "name": habit.habit_name,
                "frequency": habit.frequency,
                "streak": habit.streak
            }
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to add habit: {e}")
