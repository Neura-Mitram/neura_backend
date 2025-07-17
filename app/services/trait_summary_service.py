# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from collections import Counter
from typing import List
from app.models.user import User
from app.models.user_trait_log import UserTraitLog
from app.services.trait_drift_detector import detect_trait_drift


def generate_weekly_trait_summary(user: User, db: Session) -> str:
    """
    Generates a summary of the user's emotional tone and behavioral traits
    from the past 7 days of UserTraitLog entries, plus drift detection.
    """
    cutoff = datetime.utcnow() - timedelta(days=7)
    logs = db.query(UserTraitLog).filter(
        UserTraitLog.user_id == user.id,
        UserTraitLog.timestamp >= cutoff
    ).all()

    if not logs:
        return "Not enough data to generate your weekly personality summary yet."

    # Count trait occurrences
    trait_counts = Counter((log.trait_type, log.trait_value) for log in logs)

    emotion_summary = summarize_trait_group(trait_counts, "emotion")
    tone_summary = summarize_trait_group(trait_counts, "tone")
    motivation_summary = summarize_trait_group(trait_counts, "motivation")
    streak_summary = summarize_avg_streak(logs)
    drift_summary = detect_trait_drift(user, db)

    return (
        "Here's your personality snapshot from this week:\n\n"
        f"{emotion_summary}\n"
        f"{tone_summary}\n"
        f"{motivation_summary}\n"
        f"{streak_summary}\n"
        f"{drift_summary if drift_summary else '• No major trait drift detected.'}\n\n"
        "Let’s continue building a better rhythm next week! 🌱"
    )


def summarize_trait_group(counter: Counter, trait_type: str) -> str:
    group = {k[1]: v for k, v in counter.items() if k[0] == trait_type}
    if not group:
        return f"• No major {trait_type} trends recorded this week."

    most_common = sorted(group.items(), key=lambda x: -x[1])[:2]
    if trait_type == "emotion":
        label = "Emotionally, you mostly felt"
    elif trait_type == "tone":
        label = "Your conversations had a tone of"
    elif trait_type == "motivation":
        label = "Your drive was mostly influenced by"
    else:
        label = f"Trait summary for {trait_type}"

    values = ", ".join([f"{k} ({v}x)" for k, v in most_common])
    return f"• {label}: {values}."


def summarize_avg_streak(logs: List[UserTraitLog]) -> str:
    streaks = [
        float(log.trait_value)
        for log in logs
        if log.trait_type == "habit_streak" and is_float(log.trait_value)
    ]
    if not streaks:
        return "• No habit streak data recorded this week."

    avg = sum(streaks) / len(streaks)
    return f"• Your average habit streak was {avg:.1f} days."


def is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False
