# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from datetime import datetime
from app.models.user import User
from app.models.user_usage_stat import UserUsageStat

def track_usage_event(db: Session, user: User, usage_type: str) -> None:
    """
    Increment usage count for a specific usage_type (e.g., qna_summary, journal, goal).
    Creates entry if it doesn't exist.
    """
    stat = db.query(UserUsageStat).filter_by(user_id=user.id, usage_type=usage_type).first()

    if stat:
        stat.count += 1
        stat.last_used = datetime.utcnow()
    else:
        stat = UserUsageStat(
            user_id=user.id,
            usage_type=usage_type,
            count=1,
            last_used=datetime.utcnow()
        )
        db.add(stat)

    db.commit()
