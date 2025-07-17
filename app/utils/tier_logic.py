# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from app.models.user import User, TierLevel
from typing import Optional
from datetime import datetime, timedelta


def is_voice_ping_allowed(user: User) -> bool:
    return user.tier in [TierLevel.basic, TierLevel.pro]

def is_event_trigger_allowed(user: User) -> bool:
    return user.tier in [TierLevel.basic, TierLevel.pro]

def is_pro_user(user: User) -> bool:
    return user.tier == TierLevel.pro

def get_user_tier(user: User) -> str:
    return user.tier.name if hasattr(user.tier, "name") else str(user.tier)

def get_monthly_limit(tier: TierLevel) -> int:
    """
    Returns the monthly AI text usage limit for each tier.
    """
    if tier == TierLevel.pro:
        return 10000
    elif tier == TierLevel.basic:
        return 3000
    return 500

def get_max_memory_messages(tier: TierLevel) -> int:
    """
    Returns the max number of memory messages to retain per user, based on tier.
    """
    if tier == TierLevel.pro:
        return 500
    elif tier == TierLevel.basic:
        return 100
    return 10

def get_important_summary_limit(tier: str) -> int:
    if tier == "pro":
        return 100
    elif tier == "basic":
        return 50
    return 1  # Free

def has_emotion_insight(tier: str) -> bool:
    return True  # ✅ All tiers have emotion-enabled summaries now

def is_trait_decay_allowed(user: User) -> bool:
    """
    Determines if long-term trait decay should be applied.
    Only allowed for Basic and Pro tier users.
    """
    return user.tier in [TierLevel.basic, TierLevel.pro]

def is_trait_drift_enabled(user: User) -> bool:
    """
    Determines if trait drift detection is available for this user.
    Only Basic and Pro tiers are allowed.
    """
    return user.tier in [TierLevel.basic, TierLevel.pro]


# Private Mode

def is_in_private_mode(user) -> bool:
    if not user.is_private:
        return False
    if not user.last_private_on:
        return True

    duration = get_private_mode_duration_minutes(user)
    time_diff = datetime.utcnow() - user.last_private_on
    return time_diff.total_seconds() < duration * 60

def get_private_mode_duration_minutes(user) -> int:
    return {
        TierLevel.free: 30,
        TierLevel.basic: 120,
        TierLevel.pro: 720
    }.get(user.tier, 30)


# Retention mapping For Clean Up storage & database

def get_user_metadata_retention_days(user: User) -> Optional[int]:
    """
    Returns how many days to keep metadata in DB.
    """
    if user.tier == TierLevel.pro:
        return 180  # e.g., keep 6 months
    elif user.tier == TierLevel.basic:
        return 7
    return 1

def get_user_notification_retention_days(user: User) -> Optional[int]:
    """
    Returns how many days to keep NotificationLog entries.
    """
    if user.tier == TierLevel.pro:
        return 7
    elif user.tier == TierLevel.basic:
        return 3
    return 1

def get_user_max_message_retention_days(user: User) -> Optional[int]:
    if user.tier == TierLevel.pro:
        return 180  # e.g., keep 6 months
    elif user.tier == TierLevel.basic:
        return 30
    return 1

def get_user_interaction_log_retention_days(user: User) -> Optional[int]:
    """
    Returns how many days to keep InteractionLog entries.
    """
    if user.tier == TierLevel.pro:
        return 180  # e.g., keep 6 months
    elif user.tier == TierLevel.basic:
        return 30
    return 1

def get_user_checkin_retention_days(user: User) -> int:
    """
    Returns how many days to keep DailyCheckin entries.
    """
    if user.tier == TierLevel.pro:
        return 180
    elif user.tier == TierLevel.basic:
        return 30
    return 1

def get_user_journal_retention_days(user: User) -> int:
    """
    Returns how many days to keep JournalEntry entries.
    """
    if user.tier == TierLevel.pro:
        return 180
    elif user.tier == TierLevel.basic:
        return 90
    return 7

def get_user_completed_goal_retention_days(user: User) -> int:
    """
    Returns how many days to keep completed Goals.
    """
    if user.tier == TierLevel.pro:
        return 180
    elif user.tier == TierLevel.basic:
        return 30
    return 7

def get_user_completed_habit_retention_days(user: User) -> int:
    """
    Returns how many days to keep completed Habits.
    """
    if user.tier == TierLevel.pro:
        return 180
    elif user.tier == TierLevel.basic:
        return 30
    return 7

def get_user_mood_retention_days(user: User) -> int:
    """
    Returns how many days to keep Mood.
    """
    if user.tier == TierLevel.pro:
        return 180
    elif user.tier == TierLevel.basic:
        return 30
    return 7

def get_user_sos_retention_days(user: User) -> int:
    """
    Returns how many days to keep SOS.
    """
    if user.tier == TierLevel.pro:
        return 180
    elif user.tier == TierLevel.basic:
        return 30
    return 7

def get_trait_retention_days(user: User, trait_type: str) -> int:
    """
    Returns how many days to retain user trait logs based on tier and trait type.
    """
    tier = user.tier.name if hasattr(user.tier, "name") else str(user.tier)

    if tier == TierLevel.pro:
        return 60
    elif tier == TierLevel.basic:
        return 30
    else:  # Free
        if trait_type in ["emotion", "tone"]:
            return 7
        else:
            return 14

