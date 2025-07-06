# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from app.models.user import User, TierLevel
from typing import Optional


def is_voice_ping_allowed(user: User) -> bool:
    return user.tier in [TierLevel.basic, TierLevel.pro]

def is_event_trigger_allowed(user: User) -> bool:
    return user.tier in [TierLevel.basic, TierLevel.pro]

def is_pro_user(user: User) -> bool:
    return user.tier == TierLevel.pro


def get_monthly_limit(tier: TierLevel) -> int:
    """
    Returns the monthly AI text usage limit for each tier.
    """
    if tier == TierLevel.pro:
        return 1000
    elif tier == TierLevel.basic:
        return 300
    return 50


def get_user_audio_file_retention_days(user: User) -> int:
    """
    Returns how many days to keep audio files on disk.
    Always 1 day for all tiers.
    """
    return 1

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


