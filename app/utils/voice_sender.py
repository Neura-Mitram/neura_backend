# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


import logging
from app.utils.audio_processor import synthesize_voice
from app.models import NotificationLog
from app.models.database import SessionLocal
from datetime import datetime
import os


async def send_voice_to_neura(user_id: int, text: str) -> dict:
    """
    Directly synthesizes audio and logs the notification.
    """
    # Synthesize the TTS audio
    audio_path = synthesize_voice(
        text,
        gender="male",  # or parameterize if you want
        output_folder="/data/audio/voice_notifications"
    )

    # ✅ Extract filename
    filename = os.path.basename(audio_path)

    # Log the notification in DB
    db = SessionLocal()
    try:
        notification = NotificationLog(
            user_id=user_id,
            text=text,
            audio_url=f"voice_notifications/{filename}",
            created_at=datetime.utcnow()
        )
        db.add(notification)
        db.commit()
        logging.info(f"[VoiceSender] Synthesized audio for user {user_id}")
    except Exception as e:
        db.rollback()
        logging.error(f"[VoiceSender] Failed to log notification: {str(e)}")
        return {
            "reply": text,
            "audio_url": None
        }
    finally:
        db.close()

    # ✅ Consistent return URL
    return {
        "reply": text,
        "audio_url": f"/get-voice-chat-audio?user_id={user_id}&filename=voice_notifications/{filename}"
    }
