# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from datetime import datetime, timedelta
from fastapi import Request
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.goal import Goal
from app.models.mood import MoodLog
from app.utils.ai_engine import generate_ai_reply
from app.utils.tier_logic import is_voice_ping_allowed
from app.utils.voice_sender import store_voice_weekly_summary
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.usage_tracker import track_usage_event

async def handle_goal_weekly_summary(request: Request, user: User, message: str, db: Session):
    """
    Returns user's weekly goal progress:
    - Active
    - Completed
    - Missed (overdue)
    - AI motivational summary (emotion-aware)
    """

    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)

    active_goals = db.query(Goal).filter(
        Goal.user_id == user.id,
        Goal.status == "active"
    ).all()

    completed_goals = db.query(Goal).filter(
        Goal.user_id == user.id,
        Goal.status == "completed",
        Goal.updated_at >= week_ago
    ).all()

    overdue_goals = [
        g for g in active_goals if g.deadline and g.deadline < now
    ]

    summary_text = f"""
🗓️ Weekly Goal Progress:

✅ Completed Goals ({len(completed_goals)}):
{chr(10).join(['- ' + g.goal_text for g in completed_goals]) or 'None'}

📌 Active Goals ({len(active_goals)}):
{chr(10).join(['- ' + g.goal_text for g in active_goals]) or 'None'}

⚠️ Overdue Goals ({len(overdue_goals)}):
{chr(10).join(['- ' + g.goal_text for g in overdue_goals]) or 'None'}
    """

    # 🧠 Optional emotion-aware boost
    recent_moods = db.query(MoodLog).filter(
        MoodLog.user_id == user.id,
        MoodLog.timestamp >= week_ago
    ).all()

    emotion_counts = {}
    for mood in recent_moods:
        tone = mood.emotion_tone or "neutral"
        emotion_counts[tone] = emotion_counts.get(tone, 0) + 1

    # Sort emotions by count
    top_emotion = sorted(emotion_counts.items(), key=lambda x: -x[1])[0][0] if emotion_counts else "neutral"

    # 🧠 Generate emotion-aware AI summary
    try:
        full_prompt = f"""
The user had the following emotion trend this week: dominant emotion was *{top_emotion}*.

Write a motivational reflection summarizing their weekly goals:
- Completed: {len(completed_goals)}
- Active: {len(active_goals)}
- Missed: {len(overdue_goals)}

Use an encouraging tone that matches their emotional state.
Close with a line like "Let’s carry this energy forward" or "Let’s reset for a fresh week".
"""
        ai_summary = generate_ai_reply(inject_persona_into_prompt(user, full_prompt, db))

    except Exception:
        ai_summary = "(AI summary unavailable)"

    # ✅ Voice summary if eligible
    if is_voice_ping_allowed(user) and user.voice_nudges_enabled and user.preferred_delivery_mode == "voice":
        store_voice_weekly_summary(user, ai_summary if ai_summary and ai_summary != "(AI summary unavailable)" else summary_text, db)

    track_usage_event(db, user, category="goal_weekly_summary")

    return {
        "message": summary_text,
        "ai_summary": ai_summary,
        "dominant_emotion": top_emotion,
        "emotion_counts": emotion_counts
    }
