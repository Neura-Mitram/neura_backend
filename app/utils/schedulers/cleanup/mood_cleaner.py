# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.database import SessionLocal
from app.models.mood_log import MoodLog
from app.models.sos import SOSLog
from app.models.user import User
from app.utils.tier_logic import get_user_mood_retention_days
import logging

logger = logging.getLogger("cleanup")

def clean_old_mood_logs():
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        total_deleted = 0

        for user in users:
            retention_days = get_user_mood_retention_days(user)
            cutoff = datetime.utcnow() - timedelta(days=retention_days)

            count = (
                db.query(MoodLog)
                .filter(
                    MoodLog.user_id == user.id,
                    MoodLog.timestamp < cutoff
                )
                .delete(synchronize_session=False)
            )
            total_deleted += count

            logger.info(
                f"🧠 User {user.id} ({user.tier.value}) - Deleted {count} Mood logs older than {retention_days} days."
            )

        db.commit()
        logger.info(
            f"✅ MoodLog cleanup completed. Total records deleted: {total_deleted}"
        )

    except Exception as e:
        logger.error(
            f"🛑 MoodLog cleanup failed: {e}",
            exc_info=True
        )
    finally:
        db.close()
