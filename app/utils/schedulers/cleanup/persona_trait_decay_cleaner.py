# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.user import User
from app.models.user_trait_log import UserTraitLog
from app.models.user_traits import UserTraits
from app.utils.tier_logic import is_trait_decay_allowed, get_trait_retention_days
import logging

logger = logging.getLogger(__name__)


def clean_old_persona_traits():
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        total_deleted = 0

        users = db.query(User).filter(User.is_verified == True).all()

        for user in users:
            trait_logs = db.query(UserTraitLog).filter(
                UserTraitLog.user_id == user.id
            ).all()

            for trait in trait_logs:
                retention_days = get_trait_retention_days(user, trait.trait_type)
                if trait.timestamp < now - timedelta(days=retention_days):
                    db.delete(trait)
                    total_deleted += 1

        db.commit()
        logger.info(f"🧹 PersonaTraitDecay (Tier-Aware): Deleted {total_deleted} outdated traits.")
    except Exception as e:
        logger.warning(f"⚠️ PersonaTraitDecay cleanup failed: {e}")
    finally:
        db.close()




def decay_user_traits():
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        updated = 0
        deleted = 0

        traits = db.query(UserTraits).all()

        for trait in traits:
            user = db.query(User).filter(User.id == trait.user_id).first()
            if not user or not is_trait_decay_allowed(user):
                continue  # ❌ Skip users not allowed for trait decay

            age_days = (now - trait.last_updated).days
            original_score = trait.score

            if age_days >= 60:
                trait.score = 0.0
            elif age_days >= 45:
                trait.score = 0.3
            elif age_days >= 30:
                trait.score = 0.5
            elif age_days >= 14:
                trait.score = 0.7

            if trait.score != original_score:
                if trait.score == 0.0:
                    db.delete(trait)
                    deleted += 1
                else:
                    trait.last_updated = now
                    db.add(trait)
                    updated += 1

        db.commit()
        logger.info(f"[LongTermTraitDecay] ✅ Updated: {updated} | 🗑️ Deleted: {deleted}")
    except Exception as e:
        logger.error(f"[LongTermTraitDecay] ❌ Error: {e}")
    finally:
        db.close()
