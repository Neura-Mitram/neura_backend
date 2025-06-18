from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.models.database import SessionLocal
from app.models.user_model import User

from app.utils.trial_utils import check_trial_expiry

router = APIRouter(prefix="/auth", tags=["Anonymous Auth"])

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/anonymous-login")
def anonymous_login(device_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.temp_uid == device_id).first()

    if user:
        if user.trial_start:
            trial_info = check_trial_expiry(user.trial_start)
        else:
            trial_info = {"trial_expired": False, "days_used": 0, "days_left": 7}

        # ❌ Block usage if trial expired and tier is still "Tier 1"
        if trial_info["trial_expired"] and user.tier == "Tier 1":
            raise HTTPException(status_code=403, detail="🚫 Trial expired. Please upgrade to continue.")

        return {
            "message": "🔁 Returning user",
            "user": {
                "device_id": user.temp_uid,
                "ai_name": user.ai_name,
                "voice": user.voice,
                "tier": user.tier,
                "trial_expired": trial_info["trial_expired"],
                "days_used": trial_info["days_used"],
                "days_left": trial_info["days_left"]
            }
        }

    # 🆕 New user
    new_user = User(
        temp_uid=device_id,
        trial_start=datetime.utcnow(),
        is_verified=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "🆕 New anonymous user created",
        "user": {
            "device_id": new_user.temp_uid,
            "ai_name": new_user.ai_name,
            "voice": new_user.voice,
            "tier": new_user.tier,
            "trial_expired": False,
            "days_used": 0,
            "days_left": 7
        }
    }

@router.post("/upgrade-tier")
def upgrade_anonymous_tier(device_id: str, new_tier: str, payment_key: str, db: Session = Depends(get_db)):
    if new_tier not in ["Tier 2", "Tier 3"]:
        raise HTTPException(status_code=400, detail="Invalid tier. Choose 'Tier 2' or 'Tier 3'.")

    if not payment_key:
        raise HTTPException(status_code=400, detail="❌ Payment key is required.")

    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.tier = new_tier
    user.payment_key = payment_key
    db.commit()

    return {
        "message": f"✅ Tier upgraded to {new_tier}",
        "device_id": user.temp_uid,
        "new_tier": user.tier,
        "payment_key": user.payment_key,
    }

@router.post("/downgrade-tier")
def downgrade_tier(device_id: str, new_tier: str, db: Session = Depends(get_db)):
    if new_tier not in ["Tier 2"]:
        raise HTTPException(status_code=400, detail="❌ Downgrade only allowed to Tier 2 (from Tier 3).")

    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="❌ User not found.")

    if user.tier != "Tier 3":
        raise HTTPException(status_code=403, detail="❌ Downgrade only allowed from Tier 3.")

    user.tier = new_tier
    db.commit()

    return {
        "message": f"✅ Tier downgraded to {new_tier}",
        "device_id": user.temp_uid,
        "new_tier": user.tier
    }

@router.get("/profile")
def get_user_profile(device_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.temp_uid == device_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="❌ User not found.")

    is_upgraded = user.tier in ["Tier 2", "Tier 3"]

    return {
        "user_id": user.id,   # ✅ ADD THIS
        "device_id": user.temp_uid,
        "ai_name": user.ai_name,
        "voice": user.voice,
        "tier": user.tier,
        "is_upgraded": is_upgraded,
        "trial_start": user.trial_start.isoformat() if user.trial_start else None
    }

@router.post("/update-onboarding")
def update_onboarding(device_id: str, ai_name: str, voice: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.ai_name = ai_name
    user.voice = voice
    db.commit()

    return {"message": "✅ Onboarding updated successfully"}
