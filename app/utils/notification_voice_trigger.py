
# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


import logging
from sqlalchemy.orm import Session
from fastapi import Request
from app.models.user import User
from app.utils.voice_sender import send_voice_to_neura
from app.services.emotion_tone_updater import update_emotion_status
from app.utils.ambient_guard import is_fragile_emotion, is_gps_near_unsafe_area

logger = logging.getLogger(__name__)

def is_keyword_matched(content: str, keywords_str: str) -> bool:
    try:
        keywords = [k.strip().lower() for k in keywords_str.split(",") if k.strip()]
        return any(keyword in content.lower() for keyword in keywords)
    except Exception as e:
        logger.warning(f"⚠️ Failed to process keywords: {e}")
        return False

def build_prompt(source: str, content: str) -> str:
    return f"You just received a {source} message: {content}\nGive a short voice notification with empathy."

async def trigger_voice_if_keyword_matched(
        request: Request,
        user: User,
        source: str,
        content: str,
        db: Session) -> dict:
    # 🔕 Preference check
    if not user.instant_alerts_enabled or user.preferred_delivery_mode != "voice":
        return {"status": "skipped", "reason": "alerts or mode disabled"}

    # 🧠 Emotion suppression
    if is_fragile_emotion(user):
        logger.info(f"⚠️ Emotion too fragile. Skipping ping for user {user.id}")
        return {"status": "skipped", "reason": "fragile_emotion"}

    # 📍 Location check
    if is_gps_near_unsafe_area(user, db):
        logger.info(f"📍 Unsafe zone. Skipping ping for user {user.id}")
        return {"status": "skipped", "reason": "unsafe_location"}

    # 🔍 Keyword trigger
    if not is_keyword_matched(content, user.monitored_keywords or ""):
        return {"status": "skipped", "reason": "no_match"}

    # ✅ Build prompt
    prompt = build_prompt(source, content)
    logger.info(f"🎯 Triggering voice for {user.id}: {source}")

    # 🎙️ Send voice
    result = await send_voice_to_neura(
        request=request,
        device_id=user.temp_uid,
        text=prompt,
        gender=user.voice,
        emotion=user.emotion_status or "unknown",
        lang=user.preferred_lang or "en"
    )

    logger.info(f"✅ Voice sent to user {user.id} | status={result.get('status')}")

    # 🎭 Update emotion status after sending
    await update_emotion_status(user, prompt, db, source="notification_voice")

    return {"status": "sent", "details": result}
