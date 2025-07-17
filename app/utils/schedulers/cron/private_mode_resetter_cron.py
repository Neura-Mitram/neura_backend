# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.user import User
from app.models.database import SessionLocal
import logging

logger = logging.getLogger(__name__)

def reset_expired_private_modes():
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        timeout_minutes = 30

        expired_users = db.query(User).filter(
            User.is_private == True,
            User.last_private_on != None,
            User.last_private_on < now - timedelta(minutes=timeout_minutes)
        ).all()

        for user in expired_users:
            logger.info(f"🔄 Auto-resuming private mode for user {user.temp_uid}")
            user.is_private = False
            user.last_private_on = None

        if expired_users:
            db.commit()

    except Exception as e:
        logger.error(f"❌ Error in private_mode_resetter: {e}")
    finally:
        db.close()
