# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import APIRouter, Depends, HTTPException, Query, Header, Request
from sqlalchemy.orm import Session
from app.models.database import SessionLocal

from app.models.user import User, TierLevel
from app.utils.auth_utils import ensure_token_user_match, require_token, get_memory_messages
from app.models.message_model import Message
from app.utils.tier_logic import get_monthly_limit


from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import IntegrityError
from app.utils.ai_engine import generate_ai_reply
from datetime import datetime

from app.utils.rate_limit_utils import get_tier_limit, limiter

# Import your intent router
from app.services.intent_router_core import detect_and_route_intent
from app.schemas.intent_schemas import IntentRequest
# Import fallback
from app.services.fallback_chat_ai import handle_chat_fallback

from app.utils.red_flag_utils import detect_red_flag
from app.utils.prompt_templates import red_flag_response, creator_info_response

from app.services.emotion_tone_updater import update_emotion_status



router = APIRouter()

ASSISTANT_NAME = "Neura"  # 🔄 changeable assistant name for prompt

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ChatRequest(BaseModel):
    user_id: int
    message: str
    conversation_id: int = 1
@router.post("/chat-with-neura")
@limiter.limit(get_tier_limit)
async def chat_with_neura(
    request: Request,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    # ✅ Auth
    ensure_token_user_match(user_data["sub"], payload.user_id)

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ✅ Important tagging
    important_keywords = ["remember", "goal", "habit", "remind", "dream", "mission"]
    is_important = any(word in payload.message.lower() for word in important_keywords)

    # ✅ Monthly usage reset
    now = datetime.utcnow()
    if user.last_gpt_reset.month != now.month or user.last_gpt_reset.year != now.year:
        user.monthly_gpt_count = 0
        user.last_gpt_reset = now

    # ✅ Limit check
    monthly_limit = get_monthly_limit(user.tier)
    if user.tier == TierLevel.free:
        total_usage = user.monthly_gpt_count + user.monthly_voice_count
        if total_usage >= monthly_limit:
            return {
                "reply": f"⚠️ You've used your {monthly_limit} total messages this month. Upgrade your plan.",
                "memory_enabled": user.memory_enabled,
                "important": is_important,
                "messages_used_this_month": total_usage,
                "messages_remaining": 0
            }
    else:
        if user.monthly_gpt_count >= monthly_limit:
            return {
                "reply": f"⚠️ You've used your {monthly_limit} text messages this month. Upgrade your plan.",
                "memory_enabled": user.memory_enabled,
                "important": is_important,
                "messages_used_this_month": user.monthly_gpt_count,
                "messages_remaining": 0
            }

    # 🚩 Red flag detection
    red_flag = detect_red_flag(payload.message)
    if red_flag == "code":
        return {
            "reply": red_flag_response("code or internal details"),
            "memory_enabled": user.memory_enabled,
            "important": is_important,
            "messages_used_this_month": user.monthly_gpt_count,
            "messages_remaining": monthly_limit - user.monthly_gpt_count
        }
    if red_flag == "creator":
        return {
            "reply": creator_info_response(),
            "memory_enabled": user.memory_enabled,
            "important": is_important,
            "messages_used_this_month": user.monthly_gpt_count,
            "messages_remaining": monthly_limit - user.monthly_gpt_count
        }

    # ✅ Update emotion
    emotion_label = await update_emotion_status(user, user_query, db)

    # ✅ Detect intent first
    intent_prompt = f"""
    You are an assistant that classifies user intent.
    Return ONLY one word from this list:
    [
        journal, journal_list, journal_delete, journal_modify,
        checkin, checkin_list, checkin_delete, checkin_modify,
        habit, habit_list, habit_modify, habit_delete,
        goal, goal_list, goal_modify, goal_delete,
        search, notification, smart_reply,
        creator_mode, creator_caption, creator_content_ideas,
        creator_weekly_plan, creator_audience_helper, creator_viral_reels,
        creator_seo, creator_email, creator_time_planner,
        creator_youtube_script, creator_blog,
        fallback
    ]

    User input: {payload.message}

    Intent:
    """
    intent_raw = generate_ai_reply(intent_prompt)
    intent = intent_raw.strip().lower()

    # ✅ Fallback: do smart chat
    if intent == "fallback":
        return handle_chat_fallback(
            db=db,
            user=user,
            user_message=payload.message,
            is_important=is_important,
            conversation_id=payload.conversation_id
        )

    # ✅ Otherwise, dispatch to int_ent router

    intent_result = await detect_and_route_intent(
        request=request,
        payload=IntentRequest(
            user_id=payload.user_id,
            message=payload.message,
            conversation_id=payload.conversation_id
        ),
        db=db,
        user_data=user_data
    )

    return {
        **intent_result,
        "emotion": emotion_label
    }

class MemoryLogRequest(BaseModel):
    user_id: int
    conversation_id: int = 1
    limit: int = 10
    offset: int = 0

@router.post("/memory-log")
@limiter.limit(get_tier_limit)
def get_memory_log(
    request: Request,
    payload: MemoryLogRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.user_id)

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.memory_enabled:
        return {"message": "Memory is disabled for this user."}

    messages = get_memory_messages(db, user.id, payload.limit, offset=payload.offset, conversation_id=payload.conversation_id)

    return {
        "memory_enabled": user.memory_enabled,
        "conversation_id": payload.conversation_id,
        "messages": [
            {
                "sender": msg.sender,
                "message": msg.message,
                "timestamp": msg.timestamp.isoformat(),
                "important": msg.important
            } for msg in messages
        ]
    }
