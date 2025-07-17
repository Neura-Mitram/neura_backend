# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.goal import Goal
from app.models.user import User
from app.utils.ai_engine import generate_ai_reply
from app.utils.auth_utils import ensure_token_user_match
from fastapi import HTTPException, Request
import json
from datetime import datetime
from app.services.emotion_tone_updater import update_emotion_status
from app.utils.prompt_templates import goal_modify_prompt
from app.services.goal_progress_service import update_goal_progress
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.usage_tracker import track_usage_event


async def handle_modify_goal(request: Request, user: User, message: str, db: Session):
    # Ensure token-user match
    # await ensure_token_user_match(request, user.id)

    # 🔍 Emotion Detection
    emotion_label = await update_emotion_status(user, message, db, source="goal_modify")

    """
    Uses Mistral to identify which goal to update and the new status/details.
    """

    prompt = goal_modify_prompt(message, emotion_label)

    mistral_response = generate_ai_reply(inject_persona_into_prompt(user, prompt, db))

    try:
        parsed = json.loads(mistral_response)
        goal_id = parsed["goal_id"]
        new_status = parsed["new_status"]
        new_deadline = parsed.get("new_deadline")

        goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")

        goal.status = new_status
        if new_deadline:
            goal.deadline = datetime.strptime(new_deadline, "%Y-%m-%d")

        goal.emotion_label = emotion_label  # 💾 Optional but valuable

        # ✅ NEW: Update progress if provided
        progress_percent = parsed.get("progress_percent")
        if progress_percent is not None:
            update_goal_progress(goal, int(progress_percent))

        db.commit()
        db.refresh(goal)
        track_usage_event(db, user, category="goal_modify")

        return {
            "message": "✅ Goal updated.",
            "goal": {
                "id": goal.id,
                "goal_text": goal.goal_text,
                "status": goal.status,
                "deadline": goal.deadline.isoformat() if goal.deadline else None
            }
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to modify goal: {e}")
