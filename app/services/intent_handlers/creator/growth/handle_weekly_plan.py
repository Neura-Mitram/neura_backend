# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.auth_utils import ensure_token_user_match
from app.utils.tier_logic import is_pro_user
from app.services.emotion_tone_updater import update_emotion_status
from app.utils.ai_engine import generate_ai_reply
from app.utils.prompt_templates import weekly_plan_prompt
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.usage_tracker import track_usage_event

async def handle_creator_weekly_plan(request: Request, user: User, message: str, db: Session):
    # ✅ Validate token
    # await ensure_token_user_match(request, user.id)

    # ✅ Pro tier only
    if not is_pro_user(user):
        raise HTTPException(status_code=403, detail="🔒 This feature is only available to Pro users.")

    # 🔍 Detect emotion
    emotion_label = await update_emotion_status(user, message, db, source="creator_weekly_plan")

    topic = message.strip()

    # ✨ Generate 7-day plan
    prompt = weekly_plan_prompt(
        topic=topic,
        tone="friendly",
        assistant_name=user.ai_name or "Neura"
    )

    try:
        response = generate_ai_reply(inject_persona_into_prompt(user, prompt, db))

        # ✅ Increment usage counter
        user.monthly_creator_count += 1
        db.commit()
        track_usage_event(db, user, category="creator_weekly_plan")
        return {
            "message": "✅ 7-day content plan generated.",
            "plan": response.strip().split("\n"),
            "emotion": emotion_label
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate content plan: {str(e)}")
