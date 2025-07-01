from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models.notification import NotificationLog
from app.models.user import User
from app.utils.tier_logic import get_user_max_audio_retention_days
from app.utils.cleanup_audio_util import cleanup_audio_records
import os

def delete_old_voice_notifications():
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            retention_days = get_user_max_audio_retention_days(user)
            threshold = datetime.utcnow() - timedelta(days=retention_days)

            old_notifications = db.query(NotificationLog).filter(
                NotificationLog.user_id == user.id,
                NotificationLog.created_at < threshold,
                NotificationLog.type == "voice_nudge",
                NotificationLog.audio_file.isnot(None)
            ).all()

            cleanup_audio_records(old_notifications)
            for f in old_notifications:
                db.delete(f)

        db.commit()
        print("✅ Voice notifications cleanup completed.")
    except Exception as e:
        print(f"🛑 Voice notifications cleanup failed: {e}")
    finally:
        db.close()
