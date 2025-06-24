from datetime import datetime, timedelta, timezone

def check_trial_expiry(trial_start: datetime) -> dict:
    """
    Checks if a 7-day trial has expired based on the trial start datetime.

    Args:
        trial_start (datetime): The UTC datetime when the trial started.

    Returns:
        dict: {
            "days_used": int,
            "days_left": int,
            "trial_expired": bool
        }
    """
    # Ensure both date-times are timezone-aware and in UTC
    if trial_start.tzinfo is None:
        trial_start = trial_start.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    delta = now - trial_start

    days_used = delta.days
    days_left = max(0, 7 - days_used)
    trial_expired = days_used >= 7

    return {
        "days_used": days_used,
        "days_left": days_left,
        "trial_expired": trial_expired
    }
