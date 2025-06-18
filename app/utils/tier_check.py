from fastapi import HTTPException
from app.models.database import SessionLocal
from app.models.user_model import User
from datetime import datetime, timedelta

def get_monthly_limit(tier: str) -> int:
    limits = {
        "Tier 1": 200,
        "Tier 2": 600,
        "Tier 3": 2000  # or float('inf') if unlimited
    }
    return limits.get(tier, 200)

def ensure_minimum_tier(user_id: int, required_tier: str):
    db = SessionLocal()
    user = db.query(User).filter_by(id=user_id).first()
    db.close()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Block Tier 1 users if trial expired
    if user.tier == "Tier 1" and user.trial_start:
        trial_end = user.trial_start + timedelta(days=7)
        if datetime.utcnow() > trial_end:
            raise HTTPException(
                status_code=403,
                detail="🚫 Trial expired. Upgrade to Tier 2 or 3 to continue."
            )

    # def is_authorized(user_tier: str, required_tier: str) -> bool:
    #     tier_order = {
    #         "Tier 1": 1,
    #         "Tier 2": 2,
    #         "Tier 3": 3
    #     }
    #     return tier_order.get(user_tier, 0) >= tier_order.get(required_tier, 0)

    # if not is_authorized(user.tier, required_tier):
    #     raise HTTPException(
    #         status_code=403,
    #         detail=f"This feature requires at least {required_tier}. Your current tier: {user.tier}"
    #     )
