from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User
from app.utils.auth_utils import require_token
from app.utils.rate_limit_utils import get_tier_limit, limiter

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/profile-summary")
@limiter.limit(get_tier_limit)
async def profile_summary(
    user_data: dict = Depends(require_token),
    db: Session = Depends(get_db)
):
    user_id = int(user_data["sub"])

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "name": user.name,
        "tier": user.tier.value,
        "ai_name": user.ai_name,
        "voice": user.voice,
        "memory_enabled": user.memory_enabled,
        "monthly_gpt_count": user.monthly_gpt_count,
        "monthly_voice_count": user.monthly_voice_count,
        "monthly_creator_count": user.monthly_creator_count,
        "last_gpt_reset": user.last_gpt_reset.isoformat(),
        "goal_focus": user.goal_focus,
        "personality_mode": user.personality_mode,
        "emotion_status": user.emotion_status,
        "voice_nudges_enabled": user.voice_nudges_enabled,
        "push_notifications_enabled": user.push_notifications_enabled,
        "nudge_frequency": user.nudge_frequency,
        "nudge_last_sent": user.nudge_last_sent.isoformat() if user.nudge_last_sent else None,
        "nudge_last_type": user.nudge_last_type,
        "hourly_ping_enabled": user.hourly_ping_enabled,
        "preferred_delivery_mode": user.preferred_delivery_mode,
        "instant_alerts_enabled": user.instant_alerts_enabled,
        "output_audio_mode": user.output_audio_mode,
        "monitored_keywords": user.monitored_keywords,
        "whitelisted_apps": user.whitelisted_apps,
        "device_type": user.device_type,
        "device_token": user.device_token,
        "os_version": user.os_version,
        "last_active_at": user.last_active_at.isoformat() if user.last_active_at else None,
        "created_at": user.created_at.isoformat()
    }
