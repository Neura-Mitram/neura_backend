# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


import logging
from app.utils.audio_processor import synthesize_voice
from app.models.notification import NotificationLog
from app.models.database import SessionLocal
from datetime import datetime
from fastapi import Request
from typing import Optional
from app.models.user import User
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

async def send_voice_to_neura(
    text: str,
    device_id: str,
    gender: str = "male",
    emotion: str = "unknown",
    lang: str = "en",
    request: Optional[Request] = None
) -> dict:
    """
    Synthesizes voice and logs the notification (no file saved).
    Returns a streaming URL.
    """
    stream_url = synthesize_voice(text, gender=gender, emotion=emotion, lang=lang)

    db = SessionLocal()
    try:
        notification = NotificationLog(
            user_id=None,
            notification_type="voice_nudge",
            content=f"{text} [stream: {stream_url}]",
            delivered=False,
            timestamp=datetime.utcnow()
        )
        db.add(notification)
        db.commit()
        logger.info(f"[VoiceSender] Stream URL logged for device {device_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"[VoiceSender] Logging failed: {str(e)}")
        return {
            "reply": text,
            "audio_stream_url": None
        }
    finally:
        db.close()

    return {
        "reply": text,
        "audio_stream_url": stream_url
    }


def store_voice_weekly_summary(user: User, summary_text: str, db: Session):
    """
    Synthesizes a weekly voice summary and logs it using streaming.
    """
    try:
        voice_gender = user.voice if user.voice in ["male", "female"] else "male"
        stream_url = synthesize_voice(summary_text, gender=voice_gender)

        notification = NotificationLog(
            user_id=user.id,
            notification_type="weekly_summary_voice",
            content=f"{summary_text} [stream: {stream_url}]",
            delivered=False,
            timestamp=datetime.utcnow()
        )

        db.add(notification)
        db.commit()
        logger.info("🎧 Streamed voice summary saved for %s", user.name)

    except Exception as e:
        db.rollback()
        logger.error("⚠️ Failed to log voice summary for %s: %s", user.name, str(e))
