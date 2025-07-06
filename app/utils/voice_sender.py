# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


import logging
from app.utils.audio_processor import synthesize_voice
from app.models.notification import NotificationLog
from app.models.database import SessionLocal
from datetime import datetime
import os
from fastapi import Request
from typing import Optional

logger = logging.getLogger(__name__)

async def send_voice_to_neura(
    text: str,
    device_id: str,
    gender: str = "male",
    request: Optional[Request] = None
) -> dict:
    """
    Synthesizes voice and logs the notification.
    """
    # Synthesize audio
    audio_path = synthesize_voice(
        text,
        gender=gender,
        output_folder="/data/audio/voice_notifications"
    )

    filename = os.path.basename(audio_path)

    # Log to DB
    db = SessionLocal()
    try:
        notification = NotificationLog(
            user_id=None,  # Optional: you can adjust this if you want to link to numeric user ID
            device_id=device_id,
            text=text,
            audio_url=f"voice_notifications/{filename}",
            created_at=datetime.utcnow()
        )
        db.add(notification)
        db.commit()
        logger.info(f"[VoiceSender] Synthesized audio for device {device_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"[VoiceSender] Failed to log notification: {str(e)}")
        return {
            "reply": text,
            "audio_url": None
        }
    finally:
        db.close()

    # Build public URL
    if request:
        public_url = str(request.base_url) + f"audio/voice_notifications/{filename}"
    else:
        public_url = f"/audio/voice_notifications/{filename}"

    return {
        "reply": text,
        "audio_url": public_url
    }