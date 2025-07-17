# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.



from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.database import SessionLocal
from app.models.goal import Goal
from app.models.user import User
from app.utils.tier_logic import get_user_completed_goal_retention_days
import logging

logger = logging.getLogger("cleanup")

def clean_old_completed_goals():
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        total_deleted = 0

        for user in users:
            retention_days = get_user_completed_goal_retention_days(user)
            cutoff = datetime.utcnow() - timedelta(days=retention_days)

            count = (
                db.query(Goal)
                .filter(
                    Goal.user_id == user.id,
                    Goal.status == "completed",
                    Goal.completed_at.isnot(None),
                    Goal.completed_at < cutoff
                )
                .delete(synchronize_session=False)
            )
            total_deleted += count

            logger.info(
                f"🗑️ User {user.id} ({user.tier.value}) - Deleted {count} completed Goals older than {retention_days} days."
            )

        db.commit()
        logger.info(
            f"✅ Goal cleanup completed. Total records deleted: {total_deleted}"
        )

    except Exception as e:
        logger.error(
            f"🛑 Goal cleanup failed: {e}",
            exc_info=True
        )
    finally:
        db.close()
