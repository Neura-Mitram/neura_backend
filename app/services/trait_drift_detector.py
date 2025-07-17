# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from datetime import datetime, timedelta
from collections import Counter
from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.user_trait_log import UserTraitLog
from app.utils.tier_logic import is_trait_drift_enabled


def detect_trait_drift(user: User, db: Session) -> Optional[str]:
    """
    Detects personality drift by comparing dominant traits
    from the last 3 days vs 7–14 days ago.

    Returns a natural-language message if drift is detected,
    otherwise returns None.
    """

    # 🛡 Tier check
    if not is_trait_drift_enabled(user):
        return None

    now = datetime.utcnow()
    recent_start = now - timedelta(days=3)
    past_start = now - timedelta(days=14)
    past_end = now - timedelta(days=7)

    # Fetch logs
    recent_logs = db.query(UserTraitLog).filter(
        UserTraitLog.user_id == user.id,
        UserTraitLog.timestamp >= recent_start
    ).all()

    past_logs = db.query(UserTraitLog).filter(
        UserTraitLog.user_id == user.id,
        UserTraitLog.timestamp >= past_start,
        UserTraitLog.timestamp < past_end
    ).all()

    if not recent_logs or not past_logs:
        return None

    def summarize_dominant_traits(logs):
        counts = Counter((log.trait_type, log.trait_value) for log in logs)
        dominant = {}
        for trait_type in ["emotion", "tone", "motivation"]:
            filtered = {k[1]: v for k, v in counts.items() if k[0] == trait_type}
            if filtered:
                top_trait = sorted(filtered.items(), key=lambda x: -x[1])[0][0]
                dominant[trait_type] = top_trait
        return dominant

    recent_summary = summarize_dominant_traits(recent_logs)
    past_summary = summarize_dominant_traits(past_logs)

    drift_messages = []

    for trait_type in ["emotion", "tone", "motivation"]:
        recent_val = recent_summary.get(trait_type)
        past_val = past_summary.get(trait_type)

        if recent_val and past_val and recent_val != past_val:
            drift_messages.append(
                f"Your *{trait_type}* seems to have shifted from *{past_val}* to *{recent_val}*."
            )

    if not drift_messages:
        return None

    return "🔄 *Personality Shift Detected:*\n" + "\n".join(drift_messages)
