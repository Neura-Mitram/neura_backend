# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional, Dict, Any
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


#-------------------------------------------------------------------Sensor Events Handle ----------------------------------------------------------
# ✅ Input schema for dynamic mobile events
class EventInput(BaseModel):
    device_id: str
    event_type: str  # e.g. "sensor_context", "motion_update", "battery_update"
    metadata: Optional[Dict[str, Any]] = {}


def _hour_from_metadata_time(metadata: dict) -> Optional[int]:
    t = metadata.get("time")
    if not t:
        return None
    try:
        # support "23:45" or ISO-like "2025-08-09T23:45:00"
        if ":" in t and len(t.split(":")[0]) <= 2:
            return int(t.split(":")[0])
        if "T" in t:
            return int(t.split("T")[1].split(":")[0])
    except Exception:
        return None
    return None


def evaluate_context(event_type: str, metadata: dict) -> dict:
    """
    Produce a small, rule-driven summary: priority and human tags.
    Keep rules conservative — AI will handle wording.
    """
    priority = "normal"
    tags = []

    # Allow the native sender to override priority
    if metadata.get("priority") in ("low", "normal", "high"):
        priority = metadata.get("priority")

    # Custom prompt => treat as high-priority actionable (unless overridden)
    if metadata.get("custom_prompt"):
        priority = "high"
        tags.append("custom prompt")

    # Battery
    battery = metadata.get("battery")
    if isinstance(battery, (int, float)):
        if battery <= 10:
            priority = "high"
            tags.append("very low battery")
        elif battery <= 20 and priority != "high":
            tags.append("low battery")

    # Charging state
    if metadata.get("charging") is True:
        tags.append("charging")

    # Motion / activity
    motion = (metadata.get("motion") or "").lower()
    if motion:
        if motion in ("still", "stationary", "lying down", "sitting"):
            tags.append("inactivity")
        elif motion in ("walking", "running", "on_bike"):
            tags.append("in motion")

    # Time-of-day sensitive late-night rule
    hour = _hour_from_metadata_time(metadata)
    if hour is not None:
        if hour >= 23 or hour < 6:
            tags.append("late night")

    # Light
    light = metadata.get("light")
    if isinstance(light, (int, float)):
        # assume normalized 0..1 or raw lux; treat <0.2 as dim if normalized
        if 0 <= light <= 1:
            if light < 0.2:
                tags.append("dim environment")
        else:
            # raw lux heuristic
            if light < 30:
                tags.append("dim environment")

    # Proximity
    prox = metadata.get("proximity")
    if prox in ("near", "close"):
        tags.append("near to face / pocket")

    # Bluetooth / Car connected
    if metadata.get("bluetooth_connected") and metadata.get("bluetooth_tag") == "car":
        priority = "high"
        tags.append("driving / car connected")

    # Ambient noise (optional)
    noise = metadata.get("ambient_noise")
    if noise and isinstance(noise, str) and noise.lower() in ("loud", "noisy"):
        tags.append("noisy environment")

    # Temperature
    temp = metadata.get("temperature")
    if isinstance(temp, (int, float)) and temp >= 35:
        tags.append("hot environment")

    # Deduplicate & return
    tags = list(dict.fromkeys(tags))
    return {"priority": priority, "tags": tags}


@router.post("/event/push-mobile")
async def handle_event_push(
    payload: EventInput,
    request: Request,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    # --- token/device validation (keep as you had it) ---
    ensure_token_user_match(user_data["sub"], payload.device_id)

    # --- fetch user by device_id ---
    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found for this device_id")

    # --- tier & delivery preference checks ---
    if user.tier.value == "free" or not user.instant_alerts_enabled:
        return {"status": "skipped", "reason": "Free tier or realtime alerts disabled"}

    if user.preferred_delivery_mode != "voice":
        return {"status": "skipped", "reason": "User prefers text mode"}

    # --- fragile emotion & unsafe location checks ---
    if is_fragile_emotion(user):
        logger.info(f"⚠️ Emotion too fragile. Skipping ping for user {user.id}")
        return {"status": "skipped", "reason": "fragile_emotion"}

    if is_gps_near_unsafe_area(user, db):
        logger.info(f"📍 Unsafe zone. Skipping ping for user {user.id}")
        return {"status": "skipped", "reason": "unsafe_location"}

    # --- evaluate incoming context ---
    event_type = payload.event_type
    metadata = payload.metadata or {}
    emotion = user.emotion_status or "neutral"

    context_eval = evaluate_context(event_type, metadata)
    tags_str = ", ".join(context_eval["tags"]) or "no special conditions"

    logger.info(
        f"📡 Received event={event_type} device={payload.device_id} user={user.id} "
        f"priority={context_eval['priority']} tags=[{tags_str}] metadata={metadata}"
    )

    # --- skip trivial contexts (conservative) unless caller forces send ---
    if context_eval["priority"] == "normal" and not context_eval["tags"] and not metadata.get("always_send"):
        return {"status": "skipped", "reason": "no_significant_context"}

    # --- Build AI prompt (Jarvis-style) ---
    # If caller supplied a custom prompt, prefer that as base
    custom = metadata.get("custom_prompt")
    metadata_str = json.dumps(metadata, ensure_ascii=False)

    ai_system_intro = (
        "You are Neura, a proactive assistant similar to Jarvis. "
        "You should generate a short, friendly, situation-aware voice-first message "
        "that feels empathetic and helpful for the user."
    )

    ai_context_block = (
        f"Event type: {event_type}\n"
        f"Priority: {context_eval['priority']}\n"
        f"Tags: {tags_str}\n"
        f"User emotion: {emotion}\n"
        f"Sensor/metadata: {metadata_str}\n"
    )

    if custom:
        # Ask AI to refine the custom prompt rather than ignore it
        ai_prompt = (
            f"{ai_system_intro}\n\n"
            f"Use the user's custom prompt as the main content, improve tone and brevity:\n\n"
            f"Custom prompt: {custom}\n\n"
            f"{ai_context_block}\n"
            "Return a single short voice-friendly sentence (or two)."
        )
    else:
        ai_prompt = (
            f"{ai_system_intro}\n\n"
            f"{ai_context_block}\n"
            "Generate a short, voice-friendly, empathetic message the assistant should say now."
        )

    # --- Generate message via AI (with fallback) ---
    try:
        full_prompt = generate_ai_reply(ai_prompt)
    except Exception as e:
        logger.warning(f"⚠️ AI generation failed: {e}")
        # fallback: prefer custom prompt or a terse auto message
        full_prompt = custom if custom else f"Sensor event: {event_type}. {', '.join(context_eval['tags'])}".strip()
        if not full_prompt:
            full_prompt = "Just checking in — how are you doing?"

    # --- Log Interaction ---
    try:
        db.add(InteractionLog(
            user_id=user.id,
            source_app=event_type,
            intent="proactive_sensor_nudge",
            content=full_prompt,
            timestamp=datetime.utcnow()
        ))
        db.commit()
    except Exception as e:
        logger.warning(f"⚠️ Failed to log interaction: {e}")

    # --- Translate if needed ---
    user_lang = user.preferred_lang or "en"
    try:
        if user_lang != "en":
            full_prompt = translate(full_prompt, source_lang="en", target_lang=user_lang)
    except Exception as e:
        logger.warning(f"⚠️ Translation failed: {e}")

    # --- Send voice synthesis and return response (with fallback) ---
    try:
        result = await send_voice_to_neura(
            request=request,
            device_id=payload.device_id,
            text=full_prompt,
            gender=user.voice,
            emotion=emotion,
            lang=user_lang
        )
    except Exception as e:
        logger.error(f"❌ Voice synthesis failed: {e}")
        return {"status": "voice_failed", "fallback_text": full_prompt}

    # --- Update emotion / profile signals after sending ---
    try:
        await update_emotion_status(user, full_prompt, db, source=event_type)
    except Exception as e:
        logger.warning(f"⚠️ Failed to update emotion status: {e}")

    logger.info(f"✅ Sensor event delivered to user {user.id} | status={result.get('status')}")
    return {
        "status": "completed",
        "event_type": event_type,
        "priority": context_eval["priority"],
        "tags": context_eval["tags"],
        "prompt": full_prompt,
        "details": result
    }

#-------------------------------------------------------------------End Sensor Events Handle ----------------------------------------------------------

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
