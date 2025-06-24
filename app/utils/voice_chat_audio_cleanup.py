import os
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.user_model import TierLevel, User
from app.models.generated_audio_model import GeneratedAudio

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Define retention per user tier
TIER_RETENTION_DAYS = {
    TierLevel.free: 1,
    TierLevel.basic: 3,
    TierLevel.pro: 7,
}

AUDIO_DIR = "/data/audio"

def cleanup_old_audio() -> None:
    """
    Deletes old audio files based on user tier-specific retention policy.
    Also deletes corresponding DB records from GeneratedAudio table.
    """
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        audios = db.query(GeneratedAudio).join(User).all()

        deleted_files = 0

        for audio in audios:
            retention_days = TIER_RETENTION_DAYS.get(audio.user.tier, 1)
            file_age = now - audio.created_at

            if file_age > timedelta(days=retention_days):
                filepath = os.path.join(AUDIO_DIR, audio.filename)

                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                        logging.info(f"🗑️ Deleted audio file: {filepath}")
                    else:
                        logging.warning(f"⚠️ File not found: {filepath}")
                except Exception as file_error:
                    logging.error(f"Error deleting file {filepath}: {file_error}")

                db.delete(audio)
                deleted_files += 1

        db.commit()
        logging.info(f"✅ Audio cleanup completed. {deleted_files} files deleted.")

    except Exception as e:
        logging.error(f"❌ Error during audio cleanup: {e}")
    finally:
        db.close()
