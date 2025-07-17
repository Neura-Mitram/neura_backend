# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from fastapi import Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.utils.tier_logic import get_user_tier, is_voice_ping_allowed
from app.utils.auth_utils import generate_ai_reply
from app.models.mood import MoodLog
from app.models.goal import GoalEntry
from app.models.journal import JournalEntry
from app.models.habit import HabitReminder
from app.models.user import User
from collections import defaultdict
from app.utils.voice_sender import store_voice_weekly_summary  # ✅ Voice summary util added
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.usage_tracker import track_usage_event

async def handle_daily_summary(request: Request, user: User, message: str, db: Session):
    tier = get_user_tier(user)

    if tier == "free":
        return {
            "type": "summary",
            "message": "Weekly summary is available only for Basic and Pro users."
        }

    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)

    moods = db.query(MoodLog).filter(MoodLog.user_id == user.id, MoodLog.timestamp >= week_ago).all()
    journals = db.query(JournalEntry).filter(JournalEntry.user_id == user.id, JournalEntry.timestamp >= week_ago).all()
    goals = db.query(GoalEntry).filter(GoalEntry.user_id == user.id, GoalEntry.timestamp >= week_ago).all()
    habits = db.query(HabitReminder).filter(HabitReminder.user_id == user.id).all()

    summary_prompt = f"""You are Neura. Generate a 7-day summary based on the user's activity:
- Moods: {[m.mood_rating for m in moods]}
- Emotions: {[m.emotion_tone for m in moods]}
- Journals: {[j.text for j in journals]}
- Goals: {[g.goal_text for g in goals]}
- Habits: {[h.habit_name for h in habits]}

Be insightful, gentle, and proactive."""

    try:
        ai_summary = await generate_ai_reply(inject_persona_into_prompt(user, summary_prompt, db))

    except Exception as e:
        ai_summary = "I couldn’t generate a smart summary this time, but you’ve done your best this week 💙"

    # ✅ Trigger proactive voice summary if allowed
    if is_voice_ping_allowed(user) and user.voice_nudges_enabled and user.preferred_delivery_mode == "voice":
        store_voice_weekly_summary(user, ai_summary, db)

    track_usage_event(db, user, category="summary_daily")

    return {
        "type": "summary",
        "tier": tier,
        "text_summary": ai_summary
    }

def format_emotion_days(summary):
    """
    Formats emotion summary into a string:
    {"anxious": ["Monday", "Wednesday"]} → "anxious: Monday, Wednesday"
    """
    lines = []
    for emotion, days in summary.items():
        day_str = ", ".join(days)
        lines.append(f"- {emotion}: {day_str}")
    return "\n".join(lines)

async def handle_weekly_emotion_summary(request: Request, user: User, message: str, db: Session):
    """
    Aggregates journal emotion data for past 7 days and returns AI summary.
    """
    past_week = datetime.utcnow() - timedelta(days=7)
    entries = db.query(JournalEntry).filter(
        JournalEntry.user_id == user.id,
        JournalEntry.timestamp >= past_week
    ).all()

    if not entries:
        return {"message": "No journal entries found for the past week."}

    summary = defaultdict(list)
    for e in entries:
        label = e.emotion_label or "love"
        day = e.timestamp.strftime("%A")
        summary[label].append(day)

    emotion_pattern = format_emotion_days(summary)

    prompt = f"""
    A user wrote journals over the past week. Here's the emotional pattern:
    {emotion_pattern}

    Write a short emotional summary paragraph with warmth and empathy.
    End with a soft suggestion like 'Would you like a tip?' or 'Want to reflect on something?' if needed.
    """

    reply = await generate_ai_reply(inject_persona_into_prompt(user, prompt, db))

    try:
        track_usage_event(db, user, category="summary_daily")
    except Exception as e:
        print(f"⚠️ Usage tracking failed: {e}")

    return {
        "message": reply,
        "summary_pattern": summary
    }
