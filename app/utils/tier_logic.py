# app/utils/tier_logic.py

from app.models.user import User, TierLevel

def is_voice_ping_allowed(user: User) -> bool:
    return user.tier in [TierLevel.basic, TierLevel.pro]

def is_event_trigger_allowed(user: User) -> bool:
    return user.tier in [TierLevel.basic, TierLevel.pro]

def is_pro_user(user: User) -> bool:
    return user.tier == TierLevel.pro

def get_user_max_audio_retention_days(user: User) -> int:
    if user.tier == TierLevel.pro:
        return 7
    elif user.tier == TierLevel.basic:
        return 3
    return 1

def get_user_max_message_retention_days(user: User) -> int:
    if user.tier == TierLevel.pro:
        return 7
    elif user.tier == TierLevel.basic:
        return 3
    return 1


def get_monthly_limit(tier: TierLevel) -> int:
    """
    Returns the monthly GPT text usage limit for each tier.
    """
    if tier == TierLevel.pro:
        return 1000
    elif tier == TierLevel.basic:
        return 300
    return 50

