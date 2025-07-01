# app/services/intent_handlers/creator_utility/handle_email.py

from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.auth_utils import ensure_token_user_match
from app.utils.tier_logic import is_pro_user
from app.services.emotion_tone_updater import update_emotion_status
from app.services.mistral_ai_service import get_mistral_reply
from app.utils.prompt_templates import email_prompt

async def handle_creator_email(request: Request, user: User, message: str, db: Session):
    # ✅ Validate token
    await ensure_token_user_match(request, user.id)

    # ✅ Pro-only
    if not is_pro_user(user):
        raise HTTPException(status_code=403, detail="🔒 This feature is only available to Pro users.")

    # 🔍 Detect emotion
    emotion_label = await update_emotion_status(user, message, db)

    topic = message.strip()

    # ✨ Generate email
    prompt = email_prompt(
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
            "message": "✅ Email draft generated.",
            "email": response.strip(),
            "emotion": emotion_label
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate email draft: {str(e)}")
