# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


import logging
from sqlalchemy.orm import Session
from fastapi import Request
from app.models.user import User
from app.utils.voice_sender import send_voice_to_neura

from app.services.emotion_tone_updater import update_emotion_status

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
    if not user.instant_alerts_enabled:
        logger.info(f"🔕 Skipped: Instant alerts disabled for user {user.id}")
        return {"status": "skipped", "reason": "alerts_disabled"}

    if not user.output_audio_mode or user.preferred_delivery_mode != "voice":
        logger.info(f"🔕 Skipped: User {user.id} prefers non-voice or speaker mode not enabled")
        return {"status": "skipped", "reason": "invalid_delivery_mode"}

    matched = is_keyword_matched(content, user.monitored_keywords or "")
    if not matched:
        return {"status": "skipped", "reason": "no_keyword_match"}

    prompt = build_prompt(source, content)
    logger.info(f"🎯 Triggering voice for user {user.id}: source={source}")

    # ✅ Use device_id and voice gender
    result = await send_voice_to_neura(
        request=request,
        device_id=user.temp_uid,
        text=prompt,
        gender=user.voice
    )

    logger.info(f"🎙️ Voice sent to user {user.id} | status={result.get('status')}")

    # 🎭 Update emotion status after sending
    await update_emotion_status(user, prompt, db)

    return {"status": "sent", "details": result}
