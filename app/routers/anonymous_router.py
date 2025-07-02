from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.user import User, TierLevel
from app.utils.auth_utils import ensure_token_user_match, require_token

# from app.utils.trial_utils import check_trial_expiry
from app.utils.jwt_utils import create_access_token  # ✅ JWT added
from pydantic import BaseModel


router = APIRouter(prefix="/auth", tags=["Anonymous Auth"])

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class LoginRequest(BaseModel):
    device_id: str
@router.post("/anonymous-login")
def anonymous_login(payload: LoginRequest, db: Session = Depends(get_db)):
    device_id = payload.device_id
    user = db.query(User).filter(User.temp_uid == device_id).first()

    if user:
        token = create_access_token({"sub": user.temp_uid})
        return {
            "message": "🔁 Returning user",
            "token": token,
            "user": {
                "device_id": user.temp_uid,
                "ai_name": user.ai_name,
                "voice": user.voice,
                "tier": user.tier.value,
            }
        }

    new_user = User(
        temp_uid=device_id,
        is_verified=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({"sub": new_user.temp_uid})
    return {
        "message": "🆕 New anonymous user created",
        "token": token,
        "user": {
            "device_id": new_user.temp_uid,
            "ai_name": new_user.ai_name,
            "voice": new_user.voice,
            "tier": new_user.tier.value,
        }
    }


class OnboardingUpdateRequest(BaseModel):
    device_id: str
    ai_name: str
    voice: str
@router.post("/update-onboarding")
def update_onboarding(payload: OnboardingUpdateRequest, db: Session = Depends(get_db), user_data: dict = Depends(require_token)):
    ensure_token_user_match(user_data["sub"], payload.device_id)

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.ai_name = payload.ai_name
    user.voice = payload.voice
    db.commit()

    return {
        "message": "✅ Onboarding updated successfully",
        "device_id": user.temp_uid,
        "ai_name": user.ai_name,
        "voice": user.voice
    }


class ProfileRequest(BaseModel):
    device_id: str
@router.post("/profile")
def get_profile(payload: ProfileRequest, db: Session = Depends(get_db), user_data: dict = Depends(require_token)):
    ensure_token_user_match(user_data["sub"], payload.device_id)

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    is_upgraded = user.tier in [TierLevel.basic, TierLevel.pro]

    return {
        "device_id": user.temp_uid,
        "ai_name": user.ai_name,
        "voice": user.voice,
        "tier": user.tier.value,
        "is_upgraded": is_upgraded
    }


class TierUpgradeRequest(BaseModel):
    device_id: str
    new_tier: str
    payment_key: str
@router.post("/upgrade-tier")
def upgrade_anonymous_tier(payload: TierUpgradeRequest, db: Session = Depends(get_db), user_data: dict = Depends(require_token)):
    ensure_token_user_match(user_data["sub"], payload.device_id)
    valid_tiers = [TierLevel.basic.value, TierLevel.pro.value]
    if payload.new_tier not in valid_tiers:
        raise HTTPException(status_code=400, detail="Invalid tier. Choose 'basic' or 'pro'.")

    if not payload.payment_key:
        raise HTTPException(status_code=400, detail="❌ Payment key is required.")

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.tier = TierLevel(payload.new_tier)
    user.payment_key = payload.payment_key
    db.commit()

    return {
        "message": f"✅ Tier upgraded to {user.tier.value}",
        "device_id": user.temp_uid,
        "new_tier": user.tier.value,
        "payment_key": user.payment_key,
    }


class TierDowngradeRequest(BaseModel):
    device_id: str
    new_tier: str
@router.post("/downgrade-tier")
def downgrade_tier(payload: TierDowngradeRequest, db: Session = Depends(get_db), user_data: dict = Depends(require_token)):
    ensure_token_user_match(user_data["sub"], payload.device_id)

    if payload.new_tier != TierLevel.basic.value:
        raise HTTPException(status_code=400, detail="❌ Downgrade only allowed to 'basic' (from 'pro').")

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="❌ User not found.")

    if user.tier != TierLevel.pro:
        raise HTTPException(status_code=403, detail="❌ Downgrade only allowed from 'pro' tier.")

    user.tier = TierLevel.basic
    db.commit()

    return {
        "message": f"✅ Tier downgraded to {user.tier.value}",
        "device_id": user.temp_uid,
        "new_tier": user.tier.value
    }

