# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.user import User
from app.services.mistral_ai_service import get_mistral_reply
from app.utils.auth_utils import ensure_token_user_match
from fastapi import HTTPException, Request
import json
from app.utils.prompt_templates import smart_reply_prompt
from app.utils.red_flag_utils import detect_red_flag
from app.utils.prompt_templates import red_flag_response, creator_info_response

async def handle_smart_reply(request: Request, user: User, message: str, db: Session):
    # Ensure token-user match
    # await ensure_token_user_match(request, user.id)
    """
    Uses Mistral to generate 2–3 short, context-aware replies to a user message.
    """

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

    prompt = smart_reply_prompt(
        latest_message=message,
        assistant_name=user.ai_name or "Neura"
    )

    try:
        ai_response = await  get_mistral_reply(prompt)

        replies = json.loads(ai_response)

        if not isinstance(replies, list):
            raise ValueError("Response was not a list")

        return {
            "message": "🧠 Smart replies generated",
            "replies": replies[:3]  # limit to 3
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"⚠️ Failed to generate smart replies: {e}")
