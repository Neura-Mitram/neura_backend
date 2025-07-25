# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.models.database import SessionLocal
from app.models.user import User
from app.models.message_model import Message
from app.models.interaction_log import InteractionLog
from app.models.notification import NotificationLog
from app.utils.auth_utils import require_token, ensure_token_user_match
from app.utils.voice_sender import send_voice_to_neura
from app.utils.ai_engine import generate_ai_reply
from datetime import datetime
import logging
import json
from app.utils.notification_voice_trigger import trigger_voice_if_keyword_matched
from app.routers.safety_router import log_sos_alert
from app.services.translation_service import translate

from app.utils.location_utils import haversine_km, deliver_travel_tip
from app.utils.ambient_guard import (
    is_night_time,
    is_fragile_emotion,
    is_gps_near_unsafe_area,
    should_throttle_ping
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/event/check-nudge")
def check_nudge_fallback(
    device_id: str,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    """
    Used by native fallback on boot/unlock.
    Returns latest undelivered nudge (local or in-chat).
    """
    ensure_token_user_match(user_data["sub"], device_id)

    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ✅ Check NotificationLog first
    recent_notification = db.query(NotificationLog).filter(
        NotificationLog.user_id == user.id,
        NotificationLog.delivered == False,
        NotificationLog.notification_type.in_([
            "local_notification", "emotion_notification"
        ])
    ).order_by(NotificationLog.timestamp.desc()).first()

    if recent_notification:
        recent_notification.delivered = True
        db.commit()

        return {
            "text": recent_notification.content,
            "emoji": "💡",
            "lang": user.preferred_lang or "en"
        }

    # ✅ Fallback to in-chat prompt
    recent_prompt = db.query(Message).filter(
        Message.user_id == user.id,
        Message.is_prompt == True,
        Message.metadata.in_(["in_chat", "emotion_nudge"])
    ).order_by(Message.created_at.desc()).first()

    if recent_prompt:
        return {
            "text": recent_prompt.content,
            "emoji": "💡",
            "lang": user.preferred_lang or "en"
        }

    # ✅ No nudge to deliver
    return {
        "text": "",
        "emoji": "💡",
        "lang": user.preferred_lang or "en"
    }


# Input
# ✅ Input schema for dynamic mobile events
class EventInput(BaseModel):
    device_id: str
    event_type: str  # e.g., "spotify_open", "gmail_open", "foreground_app"
    metadata: dict = {}

@router.post("/event/push-mobile")
async def handle_event_push(
    payload: EventInput,
    request: Request,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    # ✅ Validate token and device match
    ensure_token_user_match(user_data["sub"], payload.device_id)

    # ✅ Get user by device_id
    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found for this device_id")

    # 🔕 Respect tier & preferences
    if user.tier.value == "free" or not user.instant_alerts_enabled:
        return {"status": "skipped", "reason": "Free tier or realtime alerts disabled"}
    if user.preferred_delivery_mode != "voice":
        return {"status": "skipped", "reason": "User prefers text mode"}

    # ✅ Keyword detection (smart phrases in app metadata)
    keyword_result = await trigger_voice_if_keyword_matched(
        request=request,
        user=user,
        source=payload.event_type,
        content=json.dumps(payload.metadata or {}),
        db=db
    )
    if keyword_result.get("status") == "sent":
        return {
            "status": "completed",
            "trigger_type": "keyword",
            "details": keyword_result
        }

    # ✅ Emotion-aware fallback tone mapping
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
        },
        "foreground_app": {
            "surprise": "You just opened something. Need a hand?",
            "sadness": "Using your phone again? Hope you're okay.",
            "love": "You’re back on your phone. Just checking in on you.",
        }
    }

    emotion = user.emotion_status or "love"
    metadata_str = json.dumps(payload.metadata or {}, ensure_ascii=False)

    tone_hint = base_prompts.get(payload.event_type, {}).get(
        emotion,
        "You just interacted with your phone. I'm here if you need me."
    )

    ai_prompt = (
        f"User triggered app event: {payload.event_type}\n"
        f"Emotion: {emotion}\n"
        f"App metadata: {metadata_str}\n"
        f"Tone hint: \"{tone_hint}\"\n"
        "Now generate a short, friendly, voice-first reply in a helpful tone."
    )

    try:
        full_prompt = generate_ai_reply(ai_prompt)
    except Exception as e:
        logger.warning(f"⚠️ Mistral fallback due to error: {e}")
        full_prompt = tone_hint

    logger.info(f"📲 Event: {payload.event_type} | Emotion: {emotion} | Device: {payload.device_id}")

    # ✅ Log interaction
    try:
        db.add(InteractionLog(
            user_id=user.id,
            source_app=payload.event_type,
            intent="proactive_nudge",
            content=full_prompt,
            timestamp=datetime.utcnow()
        ))
        db.commit()
    except Exception as e:
        logger.warning(f"⚠️ Failed to log interaction: {e}")

    # 🌍 Translate if needed
    user_lang = user.preferred_lang or "en"
    if user_lang != "en":
        full_prompt = translate(full_prompt, source_lang="en", target_lang=user_lang)

    # 🗣️ Send to voice
    try:
        result = await send_voice_to_neura(
            request=request,
            device_id=payload.device_id,
            text=full_prompt,
            gender=user.voice,
            emotion=emotion,
            lang=user_lang
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
        return {
            "status": "voice_failed",
            "fallback_text": full_prompt
        }



class TravelCheckInput(BaseModel):
    device_id: str
    lat: float
    lon: float

@router.post("/event/check-travel")
async def check_travel_trigger(
    payload: TravelCheckInput,
    request: Request,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.device_id)

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.last_lat or not user.last_lon:
        user.last_lat = payload.lat
        user.last_lon = payload.lon
        db.commit()
        return {"is_travel_mode": False, "status": "initialized"}

    distance_km = haversine_km(user.last_lat, user.last_lon, payload.lat, payload.lon)
    if distance_km < 100:
        return {"is_travel_mode": False, "status": "no_significant_move", "moved_km": distance_km}

    if (
        is_night_time(user)
        or is_fragile_emotion(user)
        or is_gps_near_unsafe_area(user, db)
        or should_throttle_ping(user)
    ):
        return {"is_travel_mode": False, "status": "skipped_due_to_guard", "moved_km": distance_km}

    # ✅ Send travel tip
    tip_result = await deliver_travel_tip(user, db, payload.lat, payload.lon)

    # ✅ Update user location
    user.last_lat = payload.lat
    user.last_lon = payload.lon
    db.commit()

    return {
        "is_travel_mode": True,
        "moved_km": round(distance_km, 2),
        "city_name": tip_result["city"],
        "tips": tip_result["tips"],
        "tips_audio_url": tip_result["audio_url"],
        "moment_logged": True
    }

