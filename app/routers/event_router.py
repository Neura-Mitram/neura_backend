# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.models.database import SessionLocal
from app.models.user import User
from app.models.interaction_log import InteractionLog
from app.models.journal import JournalEntry
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

    # 🧠 Emotion-aware fallback
    emotion = user.emotion_status or "love"
    metadata_str = json.dumps(payload.metadata or {}, ensure_ascii=False)

    # 1️⃣ Get Neura’s tone prompt
    tone_map = base_prompts.get(payload.event_type, {})
    base_tone = tone_map.get(emotion, "You just interacted with your phone. I'm here if you need me.")

    # 2️⃣ Create AI prompt
    ai_prompt = (
        f"User triggered app event: {payload.event_type}\n"
        f"Emotion: {emotion}\n"
        f"App metadata: {metadata_str}\n"
        f"Tone hint: \"{base_tone}\"\n"
        "Now generate a short, friendly, voice-first reply in a helpful tone."
    )

    try:
        full_prompt = generate_ai_reply(ai_prompt)
    except Exception as e:
        logger.warning(f"⚠️ Mistral fallback due to error: {e}")
        full_prompt = base_tone

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


    # ✅ Fallback voice synthesis (translated)
    user_lang = user.preferred_lang or "en"
    if user_lang != "en":
        full_prompt = translate(full_prompt, source_lang="en", target_lang=user_lang)

    try:
        result = await send_voice_to_neura(
            request=request,
            device_id=payload.device_id,
            text=full_prompt,
            gender=user.voice,
            emotion=user.emotion_status or "unknown",
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
        # ✅ Fallback to text response
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


# Wake Mode Route
class WakeWordInput(BaseModel):
    device_id: str
    wake_phrase: str  # e.g., "neura", "neura help", "go private"
    timestamp: datetime

@router.post("/event/wakeword-trigger")
async def handle_wakeword_trigger(
    payload: WakeWordInput,
    request: Request,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.device_id)

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found for this device_id")

    logger.info(f"🟢 Wake-word triggered: '{payload.wake_phrase}' | Device: {payload.device_id}")

    # 🔒 Free tier can't use passive trigger
    if user.tier.value == "free":
        return {"status": "blocked", "reason": "Wake-word only available for Basic/Pro tiers"}

    # 🚨 Emergency trigger
    if "help" in payload.wake_phrase.lower():
        await log_sos_alert(user=user, db=db, source="wakeword", emotion=user.emotion_status)
        return {"status": "sos_triggered", "action": "alert_sent"}

    # 🛡️ Enter Private Mode
    elif "private" in payload.wake_phrase.lower():
        user.is_private = True
        db.commit()
        return {"status": "private_mode_on", "action": "mic_off"}

    # 🧠 Else: general wake → reply with smart voice
    emotion = user.emotion_status or "love"
    wake_phrase = payload.wake_phrase.lower().strip()

    ai_prompt = (
        f"A user said the wake phrase '{wake_phrase}' to trigger Neura assistant.\n"
        f"The user's emotional tone is: {emotion}.\n"
        "Now generate a short, warm, voice-first assistant greeting to begin a conversation."
    )

    try:
        smart_reply = generate_ai_reply(ai_prompt)
    except Exception as e:
        logger.warning(f"⚠️ Mistral fallback due to error: {e}")
        smart_reply = "Hello! I'm listening. What's on your mind?"

    # 🌐 Translate if needed
    user_lang = user.preferred_lang or "en"
    if user_lang != "en":
        smart_reply = translate(smart_reply, source_lang="en", target_lang=user_lang)

    # ✅ Log this interaction
    try:
        log = InteractionLog(
            user_id=user.id,
            source_app="wakeword",
            intent="wakeword_greeting",
            content=smart_reply,
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.warning(f"⚠️ Failed to log wakeword interaction: {e}")

    # 🎤 Send voice reply
    try:
        result = await send_voice_to_neura(
            request=request,
            device_id=payload.device_id,
            text=smart_reply,
            gender=user.voice,
            emotion=emotion,
            lang=user_lang
        )

        return {
            "status": "wake_responded",
            "wake_phrase": wake_phrase,
            "response": result
        }
    except Exception as e:
        logger.error(f"❌ Voice synthesis failed: {str(e)}")
        return {
            "status": "voice_failed",
            "fallback_text": smart_reply
        }



