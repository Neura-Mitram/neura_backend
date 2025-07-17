# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.notification import NotificationLog
from app.models.user import User
from app.utils.tier_logic import get_user_notification_retention_days
import os
import logging

logger = logging.getLogger("cleanup")


def delete_old_notification_logs():
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            retention_days = get_user_notification_retention_days(user)
            if not retention_days:
                logger.info(f"✅ User {user.id} ({user.tier.value}) - Notifications retained indefinitely.")
                continue

            cutoff = datetime.utcnow() - timedelta(days=retention_days)
            old_logs = (
                db.query(NotificationLog)
                .filter(
                    NotificationLog.user_id == user.id,
                    NotificationLog.timestamp < cutoff
                )
                .all()
            )

            for log in old_logs:
                db.delete(log)

            db.commit()
            logger.info(
                f"🗑️ User {user.id} ({user.tier.value}) - Deleted {len(old_logs)} NotificationLog records older than {retention_days} days."
            )

        logger.info("✅ NotificationLog cleanup completed.")
    except Exception as e:
        logger.error(f"🛑 NotificationLog cleanup failed: {e}", exc_info=True)
    finally:
        db.close()
