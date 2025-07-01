from fastapi import Request
from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.auth_utils import ensure_token_user_match
from app.services.mistral_ai_service import get_mistral_reply
from app.utils.prompt_templates import fallback_chat_prompt
from app.utils.red_flag_utils import detect_red_flag
from app.utils.prompt_templates import red_flag_response, creator_info_response

from app.services.emotion_tone_updater import update_emotion_status

async def handle_fallback_ai(request: Request, db: Session, user: User, intent_payload: dict):
    try:
        await ensure_token_user_match(request, user.id)

        user_query = intent_payload.get("query", "")
        if not user_query:
            user_query = "Just say something friendly and intelligent."

        # 🚩 Red flag detection
        red_flag = detect_red_flag(user_query)
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

        # ✅ Update emotion
        emotion_label = await update_emotion_status(user, user_query, db)

        prompt = fallback_chat_prompt(user_query)

        ai_response = await get_mistral_reply(prompt)

        return {
            "status": "success",
            "intent": "fallback",
            "reply": ai_response.strip(),
            "emotion": emotion_label
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "Fallback AI handler failed",
            "detail": str(e)
        }
