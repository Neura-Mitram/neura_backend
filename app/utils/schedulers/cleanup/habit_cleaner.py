# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.database import SessionLocal
from app.models.habit import Habit
from app.models.user import User
from app.utils.tier_logic import get_user_completed_habit_retention_days
import logging

logger = logging.getLogger("cleanup")

def clean_old_completed_habits():
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        total_deleted = 0

        for user in users:
            retention_days = get_user_completed_habit_retention_days(user)
            cutoff = datetime.utcnow() - timedelta(days=retention_days)

            count = (
                db.query(Habit)
                .filter(
                    Habit.user_id == user.id,
                    Habit.status == "completed",
                    Habit.last_completed.isnot(None),
                    Habit.last_completed < cutoff
                )
                .delete(synchronize_session=False)
            )
            total_deleted += count

            logger.info(
                f"🗑️ User {user.id} ({user.tier.value}) - Deleted {count} completed Habits older than {retention_days} days."
            )

        db.commit()
        logger.info(
            f"✅ Habit cleanup completed. Total records deleted: {total_deleted}"
        )

    except Exception as e:
        logger.error(
            f"🛑 Habit cleanup failed: {e}",
            exc_info=True
        )
    finally:
        db.close()
