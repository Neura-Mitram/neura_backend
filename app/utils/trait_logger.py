# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from sqlalchemy.orm import Session
from app.models.user_trait_log import UserTraitLog
from app.models.user import User
from datetime import datetime

def log_user_trait(
    db: Session,
    user: User,
    trait_type: str,
    trait_value: str,
    source: str = "neura"
) -> None:
    """
    Stores a single trait log for the user with a source.
    Example: trait_type="emotion", trait_value="joy", source="voice_chat"
    """
    log = UserTraitLog(
        user_id=user.id,
        trait_type=trait_type,
        trait_value=trait_value,
        source=source,
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()


def bulk_log_traits(
    db: Session,
    user: User,
    traits: dict,
    source: str = "neura"
) -> None:
    """
    Bulk log multiple traits at once.
    Example:
    traits = {
        "mood_pattern": "anxious",
        "habit_streak": "low",
        "tone": "calming"
    }
    """
    logs = []
    for trait_type, trait_value in traits.items():
        log = UserTraitLog(
            user_id=user.id,
            trait_type=trait_type,
            trait_value=trait_value,
            source=source,
            timestamp=datetime.utcnow()
        )
        logs.append(log)

    if logs:
        db.add_all(logs)
        db.commit()
