# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.user import User
from app.models.goal import Goal
from app.services.mistral_ai_service import get_mistral_reply
from app.utils.auth_utils import ensure_token_user_match
from fastapi import HTTPException, Request
from datetime import datetime
import json
from app.services.emotion_tone_updater import update_emotion_status
from app.utils.prompt_templates import goal_add_prompt


async def handle_goal_add(request: Request, user: User, message: str, db: Session):
    # Ensure token-user match
    await ensure_token_user_match(request, user.id)

    # 🔍 Emotion Detection
    emotion_label = await update_emotion_status(user, message, db)

    """
    Uses Mistral to extract goal, deadline, and insight, then saves to DB.
    """
    prompt = goal_add_prompt(message, emotion_label)

    try:
        response = get_mistral_reply(prompt)
        parsed = json.loads(response)

        goal_text = parsed.get("goal_text")
        deadline_str = parsed.get("deadline")
        insight = parsed.get("ai_insight")

        if not goal_text:
            raise ValueError("Missing goal text")

        deadline = datetime.strptime(deadline_str, "%Y-%m-%d") if deadline_str else None

        new_goal = Goal(
            user_id=user.id,
            goal_text=goal_text,
            ai_insight=insight,
            deadline=deadline,
            emotion_label=emotion_label
        )
        db.add(new_goal)
        db.commit()
        db.refresh(new_goal)

        return {
            "message": "✅ Goal saved",
            "goal": {
                "text": goal_text,
                "deadline": deadline.isoformat() if deadline else None,
                "insight": insight
            }
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"🛑 Failed to extract goal info: {e}")
