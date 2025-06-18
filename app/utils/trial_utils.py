from datetime import datetime, timedelta

def check_trial_expiry(trial_start: datetime) -> dict:
    now = datetime.utcnow()
    delta = now - trial_start
    days_used = delta.days
    days_left = max(0, 7 - days_used)
    trial_expired = days_used >= 7
    return {
        "days_used": days_used,
        "days_left": days_left,
        "trial_expired": trial_expired
    }
