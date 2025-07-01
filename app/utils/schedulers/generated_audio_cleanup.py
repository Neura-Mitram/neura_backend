from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models.generated_audio import GeneratedAudio
from app.models.user import User
from app.utils.tier_logic import get_user_max_audio_retention_days
from app.utils.cleanup_audio_util import cleanup_audio_records
import os

def delete_old_audio_files():
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            retention_days = get_user_max_audio_retention_days(user)
            threshold = datetime.utcnow() - timedelta(days=retention_days)
            old_files = db.query(GeneratedAudio).filter(
                GeneratedAudio.user_id == user.id,
                GeneratedAudio.created_at < threshold
            ).all()

            cleanup_audio_records(old_files)
            for f in old_files:
                db.delete(f)

        db.commit()
        print("✅ GeneratedAudio cleanup completed.")
    except Exception as e:
        print(f"🛑 GeneratedAudio cleanup failed: {e}")
    finally:
        db.close()
