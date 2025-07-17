from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.ai_engine import generate_ai_reply
from app.utils.auth_utils import ensure_token_user_match
from fastapi import HTTPException, Request
import json
from datetime import datetime
from app.utils.prompt_templates import smart_reply_prompt
from app.utils.red_flag_utils import detect_red_flag
from app.utils.prompt_templates import red_flag_response, creator_info_response
from app.models.interaction_log import InteractionLog
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.usage_tracker import track_usage_event

async def handle_smart_reply(request: Request, user: User, message: str, db: Session):
    # Ensure token-user match
    # await ensure_token_user_match(request, user.id)

    # 🚩 Red flag detection
    red_flag = detect_red_flag(message)
    if red_flag == "code":
        return {
            "status": "success",
            "intent": "fallback",
            "reply": red_flag_response("code or internal details")
        }
    if red_flag == "creator":
        return {
            "status": "success",
            "intent": "fallback",
            "reply": creator_info_response()
        }

    # ✅ Add emotion tone into prompt
    emotion = user.emotion_status or "love"

    prompt = f"""
You are Neura, an AI assistant helping users. The user just said:

"{message}"

Their emotional tone is: **{emotion}**

Generate 2–3 short, emotionally aware reply options. Be concise, warm, and helpful. Return JSON list.

Example:
[
  "That sounds tough — I’m here.",
  "Want me to suggest something that helps?",
  "Take your time. We can go slow."
]
    """

    try:
        ai_response = generate_ai_reply(inject_persona_into_prompt(user, prompt, db))

        replies = json.loads(ai_response)

        log = InteractionLog(
            user_id=user.id,
            intent="smart_reply",
            content=message,
            emotion=user.emotion_status or "love",
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        track_usage_event(db, user, category="smart_reply")

        if not isinstance(replies, list):
            raise ValueError("Response was not a list")

        return {
            "message": "🧠 Emotion-aware smart replies generated",
            "replies": replies[:3]
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"⚠️ Failed to generate smart replies: {e}")
