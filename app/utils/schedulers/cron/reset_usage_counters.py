# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from datetime import datetime
from app.models.database import SessionLocal
from app.models.user import User

import logging

logger = logging.getLogger("cleanup")

def reset_all_usage_counters():
    """
    Resets monthly GPT, voice, and creator counts for all users.
    Updates last_gpt_reset to now.
    """
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        total_reset = 0
        for user in users:
            user.monthly_gpt_count = 0
            user.monthly_voice_count = 0
            user.monthly_creator_count = 0
            user.last_gpt_reset = datetime.utcnow()
            total_reset += 1
        db.commit()
        logger.info(f"✅ Monthly usage counters reset for {total_reset} users.")
    except Exception as e:
        logger.error(f"🛑 Failed to reset usage counters: {e}", exc_info=True)
    finally:
        db.close()
