# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from collections import Counter
from app.models.database import SessionLocal
from app.models.user_traits import UserTraits
from app.models.user_trait_log import UserTraitLog
from app.models.user_usage_stat import UserUsageStat
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

def generate_memory_snapshot(user_id: int) -> dict:
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()

        # 1. Persistent Traits (UserTraits)
        trait_records = db.query(UserTraits).filter(UserTraits.user_id == user_id).all()
        top_traits = sorted(trait_records, key=lambda t: t.score, reverse=True)
        top_trait_names = [t.trait_name for t in top_traits if t.score >= 0.5]

        # 2. Emotion Trend (UserTraitLog - last 7 days)
        recent_logs = db.query(UserTraitLog).filter(
            UserTraitLog.user_id == user_id,
            UserTraitLog.trait_type == "emotion",
            UserTraitLog.timestamp >= now - timedelta(days=7)
        ).all()
        emotion_freq = Counter(log.trait_value for log in recent_logs)
        top_emotions = emotion_freq.most_common(2)
        emotion_summary = ", ".join(f"{k} ({v}x)" for k, v in top_emotions) if top_emotions else "N/A"

        # 3. Usage Stats (UserUsageStat)
        usage_records = db.query(UserUsageStat).filter(UserUsageStat.user_id == user_id).all()
        active_modules = [u.usage_type for u in usage_records if (now - u.last_used).days <= 7]
        inactive_modules = [u.usage_type for u in usage_records if (now - u.last_used).days > 7]

        # 4. Last active timestamp
        last_used_time = max([u.last_used for u in usage_records], default=None)
        last_active_days = (now - last_used_time).days if last_used_time else None

        # 5. Text Summary
        summary = ""
        if top_trait_names:
            summary += f"Persistent traits: {', '.join(top_trait_names)}. "
        else:
            summary += "No long-term traits detected. "

        summary += f"Recent emotional state: {emotion_summary}. "

        if active_modules:
            summary += f"Active features: {', '.join(active_modules)}. "
        if inactive_modules:
            summary += f"Inactive features: {', '.join(inactive_modules)}. "
        if last_active_days is not None:
            summary += f"Last active {last_active_days} day(s) ago."

        return {
            "user_id": user_id,
            "top_traits": top_trait_names,
            "emotion_summary": emotion_summary,
            "active_modules": active_modules,
            "inactive_modules": inactive_modules,
            "last_active_days": last_active_days,
            "summary": summary.strip()
        }

    except Exception as e:
        logger.error(f"[MemorySnapshot] ❌ Error generating snapshot for user {user_id}: {e}")
        return {}
    finally:
        db.close()
