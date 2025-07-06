# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.models.database import SessionLocal
from app.models.user import User
from app.models.interaction_log import InteractionLog
from app.utils.auth_utils import require_token, ensure_token_user_match
from app.utils.voice_sender import send_voice_to_neura
from datetime import datetime
import logging
import json
from app.utils.notification_voice_trigger import trigger_voice_if_keyword_matched

router = APIRouter()
logger = logging.getLogger(__name__)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Input
class EventInput(BaseModel):
    device_id: str
    event_type: str  # e.g., "spotify_open", "gmail_open", "call_start"
    metadata: dict = {}  # Optional additional context

@router.post("/push/event")
async def handle_event_push(
    payload: EventInput,
    request: Request,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    # ✅ Check token-user match
    ensure_token_user_match(user_data["sub"], payload.device_id)

    # ✅ Lookup user by device_id
    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found for this device_id")

    # 🔕 Skip if user preferences disable this feature
    if user.tier.value == "free" or not user.instant_alerts_enabled:
        return {"status": "skipped", "reason": "Free tier or realtime alerts disabled"}

    if user.preferred_delivery_mode != "voice":
        return {"status": "skipped", "reason": "User prefers text mode"}

    # ✅ Keyword-triggered voice notification
    keyword_result = await trigger_voice_if_keyword_matched(
        request=request,
        user=user,
        source=payload.event_type,
        content=json.dumps(payload.metadata or {}),
        db=db
    )

    # 🛑 If keyword triggered, short-circuit and return
    if keyword_result.get("status") == "sent":
        return {
            "status": "completed",
            "trigger_type": "keyword",
            "details": keyword_result
        }

    # ✅ Build fallback event prompt
    emotion = user.emotion_status or "love"
    context = f"Context: {payload.metadata}" if payload.metadata else ""

    base_prompts = {
        "spotify_open": {
            "surprise": "Looks like you're diving into music. Anything on your mind?",
            "sadness": "Some music to relax? Take a deep breath. I'm here.",
            "love": "Music is a good escape. Be kind to yourself today.",
        },
        "gmail_open": {
            "surprise": "Checking your email? Hope it's all manageable!",
            "sadness": "Don't let work emails ruin your day. You're doing great.",
            "love": "Emails can wait. But your rest matters too.",
        },
        "call_start": {
            "surprise": "All the best for your call. Be confident!",
            "sadness": "Take it easy. You're in control.",
            "love": "Keep it short if you’re tired. You’ve got this.",
        },
        "calendar_open": {
            "surprise": "Let’s plan the day. Anything exciting coming up?",
            "sadness": "One thing at a time. You’ve got this.",
            "love": "Don’t overbook yourself. Energy is precious.",
        }
    }

    fallback_prompt = "You just interacted with your phone. How can I help today?"

    prompt_variants = base_prompts.get(payload.event_type, {})
    tone_prompt = prompt_variants.get(emotion, fallback_prompt)
    full_prompt = f"{tone_prompt} {context}".strip()

    logger.info(f"📲 Event trigger: {payload.event_type} | Emotion: {emotion} | Device: {payload.device_id}")

    # ✅ Log to InteractionLog
    try:
        log = InteractionLog(
            user_id=user.id,
            source_app=payload.event_type,
            intent="proactive_nudge",
            content=full_prompt,
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.warning(f"⚠️ Failed to log interaction: {e}")

    # ✅ Fallback voice synthesis
    try:
        result = await send_voice_to_neura(
            request=request,
            device_id=payload.device_id,
            text=full_prompt,
            gender=user.voice
        )
        return {
            "status": "completed",
            "keyword_trigger": keyword_result,
            "event_trigger": {
                "prompt": full_prompt,
                "details": result
            },
            "emotion": emotion
        }
    except Exception as e:
        logger.error(f"❌ Voice synthesis failed: {str(e)}")
        # ✅ Fallback to text response
        return {
            "status": "voice_failed",
            "fallback_text": full_prompt
        }