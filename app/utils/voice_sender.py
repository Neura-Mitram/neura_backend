# app/utils/voice_sender.py

import logging
from app.utils.audio_processor import synthesize_voice
from app.models import NotificationLog
from app.models.database import SessionLocal
from datetime import datetime


async def send_voice_to_neura(user_id: int, text: str) -> dict:
    """
    Directly synthesizes audio and logs the notification.
    """
    # Synthesize the TTS audio
    audio_filename = synthesize_voice(text)

    # Log the notification in DB
    db = SessionLocal()
    try:
        notification = NotificationLog(
            user_id=user_id,
            text=text,
            audio_url=f"/audio/voice_notifications/{audio_filename}",
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

    return {
        "reply": text,
        "audio_url": f"/audio/{audio_filename}"
    }
