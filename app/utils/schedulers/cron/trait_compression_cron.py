# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.



from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from collections import Counter
import logging

from app.models.database import SessionLocal
from app.models.user import User
from app.models.user_trait_log import UserTraitLog
from app.models.user_trait_summary import UserTraitSummary
from app.utils.tier_logic import is_trait_decay_allowed, get_trait_retention_days

logger = logging.getLogger(__name__)

def compress_old_traits():
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        total_summaries = 0

        users = db.query(User).filter(User.is_active == True).all()

        for user in users:
            if not is_trait_decay_allowed(user):
                continue

            trait_logs = db.query(UserTraitLog).filter(
                UserTraitLog.user_id == user.id
            ).all()

            grouped_logs = {}

            for log in trait_logs:
                retention_days = get_trait_retention_days(user, log.trait_type)
                # Compress if between 30–retention_days ago
                if retention_days > 30:
                    start_range = now - timedelta(days=retention_days)
                    end_range = now - timedelta(days=30)
                    if start_range <= log.timestamp < end_range:
                        grouped_logs.setdefault(log.trait_type, []).append(log.trait_value)

            for trait_type, values in grouped_logs.items():
                if not values:
                    continue
                count = Counter(values)
                dominant_value, frequency = count.most_common(1)[0]

                summary = UserTraitSummary(
                    user_id=user.id,
                    trait_type=trait_type,
                    trait_value=dominant_value,
                    frequency=frequency,
                    from_date=now - timedelta(days=30),
                    to_date=now,
                    created_at=now
                )
                db.add(summary)
                total_summaries += 1

        db.commit()
        logger.info(f"[TraitCompression] ✅ Compressed trait patterns for {total_summaries} entries.")
    except Exception as e:
        logger.error(f"[TraitCompression] ❌ Error: {e}")
    finally:
        db.close()
