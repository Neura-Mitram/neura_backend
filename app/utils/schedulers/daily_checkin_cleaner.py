# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.daily_checkin import DailyCheckin
from app.models.user import User
from app.utils.tier_logic import get_user_checkin_retention_days
import logging

logger = logging.getLogger("cleanup")

def clean_old_checkins():
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        total_deleted = 0

        for user in users:
            retention_days = get_user_checkin_retention_days(user)
            cutoff = datetime.utcnow() - timedelta(days=retention_days)

            count = (
                db.query(DailyCheckin)
                .filter(
                    DailyCheckin.user_id == user.id,
                    DailyCheckin.date < cutoff.date()
                )
                .delete(synchronize_session=False)
            )
            total_deleted += count

            logger.info(
                f"🗑️ User {user.id} ({user.tier.value}) - Deleted {count} DailyCheckins older than {retention_days} days."
            )

        db.commit()
        logger.info(
            f"✅ DailyCheckin cleanup completed. Total records deleted: {total_deleted}"
        )

    except Exception as e:
        logger.error(
            f"🛑 DailyCheckin cleanup failed: {e}",
            exc_info=True
        )
    finally:
        db.close()
