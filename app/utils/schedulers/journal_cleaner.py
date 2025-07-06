# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.database import SessionLocal
from app.models.journal_entry import JournalEntry
from app.models.user import User
from app.utils.tier_logic import get_user_journal_retention_days
import logging

logger = logging.getLogger("cleanup")

def clean_old_journal_entries():
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        total_deleted = 0

        for user in users:
            retention_days = get_user_journal_retention_days(user)
            cutoff = datetime.utcnow() - timedelta(days=retention_days)

            count = (
                db.query(JournalEntry)
                .filter(
                    JournalEntry.user_id == user.id,
                    JournalEntry.timestamp < cutoff
                )
                .delete(synchronize_session=False)
            )
            total_deleted += count

            logger.info(
                f"🗑️ User {user.id} ({user.tier.value}) - Deleted {count} JournalEntries older than {retention_days} days."
            )

        db.commit()
        logger.info(
            f"✅ JournalEntry cleanup completed. Total records deleted: {total_deleted}"
        )

    except Exception as e:
        logger.error(
            f"🛑 JournalEntry cleanup failed: {e}",
            exc_info=True
        )
    finally:
        db.close()
