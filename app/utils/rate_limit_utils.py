from fastapi import Request, HTTPException, Depends
from app.utils.auth_utils import require_token
from app.models.database import SessionLocal
from app.models.user_model import User, TierLevel

# Define tier-specific limits (requests per minute)
TIER_RATES = {
    TierLevel.free.value: "5/minute",
    TierLevel.basic.value: "20/minute",
    TierLevel.pro.value: "60/minute",
}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 🔑 Key function for SlowAPI that checks tier and returns a unique key for limiting
async def get_tier_limit(request: Request, user_data: dict = Depends(require_token), db=Depends(get_db)) -> str:
    user_sub = user_data.get("sub")
    user = db.query(User).filter(User.id == user_sub).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Get tier rate or fallback to free
    tier = user.tier.value if user.tier else TierLevel.free.value
    return TIER_RATES.get(tier, "5/minute")
