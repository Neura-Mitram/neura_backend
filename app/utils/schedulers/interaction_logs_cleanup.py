# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.interaction_log import InteractionLog
from app.models.user import User
from app.models.database import SessionLocal
from app.utils.tier_logic import get_user_max_audio_retention_days

def clean_old_interaction_logs():
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            retention_days = get_user_max_audio_retention_days(user)
            cutoff = datetime.utcnow() - timedelta(days=retention_days)
            db.query(InteractionLog).filter(
                InteractionLog.user_id == user.id,
                InteractionLog.created_at < cutoff
            ).delete()
        db.commit()
        print("✅ InteractionLog cleanup completed.")
    except Exception as e:
        print(f"🛑 InteractionLog cleanup failed: {e}")
    finally:
        db.close()
