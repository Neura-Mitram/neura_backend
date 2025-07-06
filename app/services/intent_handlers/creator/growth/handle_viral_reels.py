# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.auth_utils import ensure_token_user_match
from app.utils.tier_logic import is_pro_user
from app.services.emotion_tone_updater import update_emotion_status
from app.services.mistral_ai_service import get_mistral_reply
from app.utils.prompt_templates import viral_reels_prompt


async def handle_creator_viral_reels(request: Request, user: User, message: str, db: Session):
    # ✅ Validate token
    # await ensure_token_user_match(request, user.id)

    # ✅ Pro-only
    if not is_pro_user(user):
        raise HTTPException(status_code=403, detail="🔒 This feature is only available to Pro users.")

    # 🔍 Detect emotion
    emotion_label = await update_emotion_status(user, message, db)

    topic = message.strip()

    # ✨ Generate viral Reels concepts
    prompt = viral_reels_prompt(
        topic=topic,
        tone="friendly",
        assistant_name=user.ai_name or "Neura"
    )

    try:
        response = get_mistral_reply(prompt)
        # ✅ Increment usage counter
        user.monthly_creator_count += 1
        db.commit()
        return {
            "message": "✅ Viral Reels concepts generated.",
            "ideas": response.strip().split("\n"),
            "emotion": emotion_label
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Reels concepts: {str(e)}")
