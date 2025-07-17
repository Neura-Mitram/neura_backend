# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.message_model import Message
from app.models.user import User
from app.utils.tier_logic import get_user_max_message_retention_days
from datetime import datetime, timedelta

import logging

logger = logging.getLogger("cleanup")

def delete_old_unimportant_messages():
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        total_deleted = 0

        for user in users:
            retention_days = get_user_max_message_retention_days(user)
            cutoff = datetime.utcnow() - timedelta(days=retention_days)

            count = (
                db.query(Message)
                .filter(
                    Message.user_id == user.id,
                    Message.important == False,
                    Message.timestamp < cutoff
                )
                .delete(synchronize_session=False)
            )
            total_deleted += count

            logger.info(
                f"🗑️ User {user.id} ({user.tier.value}) - Deleted {count} unimportant messages older than {retention_days} days."
            )

        db.commit()
        logger.info(
            f"✅ Message cleanup completed. Total unimportant messages deleted: {total_deleted}"
        )

    except Exception as e:
        logger.error(
            f"🛑 Message cleanup failed: {e}",
            exc_info=True
        )
    finally:
        db.close()
