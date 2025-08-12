# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

import os
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.user import User, TierLevel
from app.utils.auth_utils import ensure_token_user_match, require_token
from app.models.message_model import Message
from app.utils.tier_logic import get_monthly_limit
from pydantic import BaseModel
from datetime import datetime

from app.services.intent_router_core import detect_and_route_intent
from app.schemas.intent_schemas import IntentRequest
from app.services.fallback_chat_ai import handle_chat_fallback
from app.utils.red_flag_utils import detect_red_flag, SEVERE_KEYWORDS
from app.utils.prompt_templates import red_flag_response, creator_info_response, self_query_response
from app.services.emotion_tone_updater import update_emotion_status
from app.utils.ai_engine import generate_ai_reply
from app.services.persona_engine import run_persona_engine
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.models.sos_contact import SOSContact
from app.services.translation_service import translate

router = APIRouter(prefix="/chat", tags=["Chat Auth"])
ASSISTANT_NAME = "Neura"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ChatRequest(BaseModel):
    device_id: str
    message: str
    conversation_id: int = 1

@router.post("/chat-with-neura")
async def chat_with_neura(
    request: Request,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.device_id)

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()

    # ✅ Check if at least one SOS contact is saved
    has_sos_contact = db.query(SOSContact).filter(SOSContact.device_id == payload.device_id).first()
    if not has_sos_contact:
        return {
            "reply": "🛡️ Please add an SOS contact to continue. This is required for your safety.",
            "require_sos_contact": True
        }

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 🌐 Translate input
    user_lang = user.preferred_lang or "en"
    if user_lang != "en":
        original_text = payload.message
        payload.message = translate(original_text, source_lang=user_lang, target_lang="en")

    is_important = any(word in payload.message.lower() for word in ["remember", "goal", "habit", "remind", "dream", "mission"])

    now = datetime.utcnow()
    if user.last_gpt_reset.month != now.month or user.last_gpt_reset.year != now.year:
        user.monthly_gpt_count = 0
        user.last_gpt_reset = now

    monthly_limit = get_monthly_limit(user.tier)
    if user.tier == TierLevel.free and (user.monthly_gpt_count + user.monthly_voice_count) >= monthly_limit:
        return {
            "reply": f"⚠️ You've used your {monthly_limit} total messages this month. Upgrade your plan.",
            "memory_enabled": user.memory_enabled,
            "important": is_important,
            "messages_used_this_month": user.monthly_gpt_count,
            "messages_remaining": 0
        }
    elif user.tier != TierLevel.free and user.monthly_gpt_count >= monthly_limit:
        return {
            "reply": f"⚠️ You've used your {monthly_limit} text messages this month. Upgrade your plan.",
            "memory_enabled": user.memory_enabled,
            "important": is_important,
            "messages_used_this_month": user.monthly_gpt_count,
            "messages_remaining": 0
        }

    # 🚩 Red flag detection
    red_flag = detect_red_flag(payload.message)
    ai_name = user.ai_name or "Neura"

    if red_flag == "code":
        reply_text = red_flag_response(reason="code or internal details", lang=user_lang)
        return {
            "reply": reply_text,
            "memory_enabled": user.memory_enabled,
            "important": is_important,
            "messages_used_this_month": user.monthly_gpt_count,
            "messages_remaining": monthly_limit - user.monthly_gpt_count
        }

    if red_flag == "creator":
        reply_text = creator_info_response(lang=user_lang)
        return {
            "reply": reply_text,
            "memory_enabled": user.memory_enabled,
            "important": is_important,
            "messages_used_this_month": user.monthly_gpt_count,
            "messages_remaining": monthly_limit - user.monthly_gpt_count
        }

    if red_flag == "self_query":
        reply_text = self_query_response(ai_name=ai_name, lang=user_lang)
        return {
            "reply": reply_text,
            "memory_enabled": user.memory_enabled,
            "important": is_important,
            "messages_used_this_month": user.monthly_gpt_count,
            "messages_remaining": monthly_limit - user.monthly_gpt_count
        }

    if red_flag == "sos":
        is_force = any(term in payload.message.lower() for term in SEVERE_KEYWORDS)
        reply_text = "🚨 Emergency detected. Triggering SOS alert."
        return {
            "reply": reply_text,
            "trigger_sos": True,
            "trigger_sos_force": is_force,
            "memory_enabled": user.memory_enabled,
            "important": is_important,
            "messages_used_this_month": user.monthly_gpt_count,
            "messages_remaining": monthly_limit - user.monthly_gpt_count
        }

    emotion_label = await update_emotion_status(user, payload.message, db, source="chat")
    await run_persona_engine(db, user)

    intent_prompt = f"""
    You are an assistant that classifies user intent.
    Return ONLY one word from this list:
    [journal, journal_list, journal_delete, journal_modify,
     checkin, checkin_list, checkin_delete, checkin_modify,
     habit, habit_list, habit_modify, habit_delete,
     goal, goal_list, goal_modify, goal_delete,
     search, notification, smart_reply,
     creator_mode, creator_caption, creator_content_ideas,
     creator_weekly_plan, creator_audience_helper, creator_viral_reels,
     creator_seo, creator_email, creator_time_planner,
     creator_youtube_script, creator_blog,
     fallback]
    User input: {payload.message}
    Intent:
    """
    intent_raw = generate_ai_reply(inject_persona_into_prompt(user, intent_prompt, db))
    intent = intent_raw.strip().lower()

    if intent == "fallback":
        fallback_result = await handle_chat_fallback(
            db=db,
            user=user,
            user_message=payload.message,
            is_important=is_important,
            conversation_id=payload.conversation_id,
        )

        # 🌐 Translate fallback reply to user's language
        if user_lang != "en" and "reply" in fallback_result:
            fallback_result["reply"] = translate(fallback_result["reply"], source_lang="en", target_lang=user_lang)

        fallback_result.update({
            "messages_used_this_month": user.monthly_gpt_count,
            "messages_remaining": monthly_limit - user.monthly_gpt_count,
            "important": is_important
        })
        return fallback_result

    intent_result = await detect_and_route_intent(
        request=request,
        payload=IntentRequest(
            user_id=user.id,
            message=payload.message,
            conversation_id=payload.conversation_id
        ),
        db=db,
        user_data=user_data
    )

    # 🌐 Translate intent reply if needed
    if user_lang != "en" and "reply" in intent_result:
        intent_result["reply"] = translate(intent_result["reply"], source_lang="en", target_lang=user_lang)

    return {
        **intent_result,
        "emotion": emotion_label,
        "memory_enabled": user.memory_enabled,
        "messages_used_this_month": user.monthly_gpt_count,
        "messages_remaining": monthly_limit - user.monthly_gpt_count,
        "important": is_important
    }
