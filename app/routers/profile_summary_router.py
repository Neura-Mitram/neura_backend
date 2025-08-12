# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.user import User
from app.models.message_model import Message
from app.models.journal import JournalEntry
from app.models.daily_checkin import DailyCheckin
from app.models.goal import Goal
from app.models.habit import Habit
from app.models.sos import SOSLog
from app.models.user_usage_stat import UserUsageStat
from app.utils.auth_utils import require_token
from app.utils.tier_logic import (
    get_monthly_limit,
    get_max_memory_messages,
    get_important_summary_limit,
    has_emotion_insight,
    is_trait_decay_allowed,
    is_trait_drift_enabled,
    get_private_mode_duration_minutes,
    get_user_metadata_retention_days,
    get_user_notification_retention_days,
    get_user_max_message_retention_days,
    get_user_interaction_log_retention_days,
    get_user_checkin_retention_days,
    get_user_journal_retention_days,
    get_user_completed_goal_retention_days,
    get_user_completed_habit_retention_days,
    get_user_mood_retention_days,
    get_user_sos_retention_days
)
from app.services.smart_snapshot_generator import generate_memory_snapshot


router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/profile-summary")
async def profile_summary(
    request: Request,
    device_id: str = Query(..., description="The device_id assigned during anonymous login"),
    user_data: dict = Depends(require_token),
    db: Session = Depends(get_db)
):
    """
        Returns all profile details for the user identified by device_id.
    """

    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found for this device_id")

    return {
        "device_id": user.temp_uid,
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


@router.get("/user/tier-info")
async def get_tier_info(
    request: Request,
    device_id: str = Query(...),
    user_data: dict = Depends(require_token),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "tier": user.tier.value,
        "monthly_text_limit": get_monthly_limit(user.tier),
        "monthly_voice_limit": get_monthly_limit(user.tier),
        "max_memory_messages": get_max_memory_messages(user.tier),
        "important_summary_limit": get_important_summary_limit(user.tier.value),
        "emotions_enabled": has_emotion_insight(user.tier.value),
        "trait_decay_enabled": is_trait_decay_allowed(user),
        "trait_drift_enabled": is_trait_drift_enabled(user),
        "private_mode_minutes": get_private_mode_duration_minutes(user),
        "retention_days": {
            "metadata": get_user_metadata_retention_days(user),
            "notifications": get_user_notification_retention_days(user),
            "messages": get_user_max_message_retention_days(user),
            "interaction_logs": get_user_interaction_log_retention_days(user),
            "journal": get_user_journal_retention_days(user),
            "habits": get_user_completed_habit_retention_days(user),
            "goals": get_user_completed_goal_retention_days(user),
            "checkins": get_user_checkin_retention_days(user),
            "mood_logs": get_user_mood_retention_days(user),
            "sos_logs": get_user_sos_retention_days(user)
        }
    }


@router.get("/export/personality")
async def export_personality_snapshot(
    request: Request,
    device_id: str = Query(..., description="The device_id assigned during anonymous login"),
    user_data: dict = Depends(require_token),
    db: Session = Depends(get_db)
):
    """
    Export a user's personality & usage snapshot for transparency and insight.
    """

    # 🧠 Find user
    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    snapshot = generate_memory_snapshot(user.id)

    return {
        "status": "success",
        "device_id": user.temp_uid,
        "user_name": user.name or "Anonymous",
        "tier": user.tier.value,
        "ai_name": user.ai_name,
        "voice": user.voice,
        "preferred_language": user.preferred_lang,
        "personality_mode": user.personality_mode,
        "emotion_status": user.emotion_status,
        "summary": snapshot.get("summary", "No summary available."),
        "top_traits": snapshot.get("top_traits", []),
        "emotion_summary": snapshot.get("emotion_summary", "Not enough emotional data."),
        "active_modules": snapshot.get("active_modules", []),
        "inactive_modules": snapshot.get("inactive_modules", []),
        "last_active_days": snapshot.get("last_active_days", None),
    }



@router.get("/admin/stats")
async def admin_dashboard_stats(db: Session = Depends(get_db)):
    try:
        return {
            "total_users": db.query(User).count(),
            "total_messages": db.query(Message).count(),
            "total_journals": db.query(JournalEntry).count(),
            "total_checkins": db.query(DailyCheckin).count(),
            "total_goals": db.query(Goal).count(),
            "total_habits": db.query(Habit).count(),
            "sos_triggers": db.query(SOSLog).count(),
            "trait_snapshots": db.query(UserUsageStat).count()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
