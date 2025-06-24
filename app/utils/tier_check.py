from fastapi import HTTPException
from app.models.database import SessionLocal
from app.models.user_model import User, TierLevel
from datetime import datetime, timedelta

# ------------------- Monthly Message Limit -------------------
def get_monthly_limit(tier: str) -> int:
    """
    Returns the monthly usage limit based on tier.
    """
    limits = {
        TierLevel.free: 200,
        TierLevel.basic: 600,
        TierLevel.pro: 2000
    }
    return limits.get(tier, 200)


# ------------------- Tier Access Enforcement -------------------
def ensure_minimum_tier(user_id: int, required_tier: TierLevel):
    """
    Ensures the user has at least the required tier. Raises HTTPException otherwise.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Trial expiration logic for basic
        if user.tier == TierLevel.free and user.trial_start:
            trial_end = user.trial_start + timedelta(days=7)
            if datetime.utcnow() > trial_end:
                raise HTTPException(
                    status_code=403,
                    detail="🚫 Trial expired. Upgrade to Basic or Pro to continue."
                )

        tier_rank = {
            TierLevel.free: 1,
            TierLevel.basic: 2,
            TierLevel.pro: 3
        }

        if tier_rank[user.tier] < tier_rank[required_tier]:
            raise HTTPException(
                status_code=403,
                detail=f"This feature requires at least {required_tier.value}. Your current tier: {user.tier.value}"
            )
    finally:
        db.close()
