# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.models.user import User
from app.models.mood import MoodLog
from app.models.habit import Habit
from app.models.journal import JournalEntry
from app.models.goal import Goal
from app.models.daily_checkin import DailyCheckin
from app.models.message_model import Message
from app.utils.trait_logger import bulk_log_traits
import logging

logger = logging.getLogger(__name__)

async def run_persona_engine(db: Session, user: User) -> dict:
    """
    Dynamically generates smart traits from usage patterns.
    Updates the trait logs (via bulk_log_traits) and returns the traits dictionary.
    """
    traits = {
        "tone": "neutral",
        "habit_streak": "unknown",
        "motivation": "unknown",
        "recent_emotion": "unknown",
        "usage_pattern": "general"
    }

    try:
        # 1. Emotion trend
        recent_moods = (
            db.query(MoodLog)
            .filter(MoodLog.user_id == user.id)
            .order_by(MoodLog.timestamp.desc())
            .limit(5)
            .all()
        )
        if recent_moods:
            mood_freq = {}
            for m in recent_moods:
                mood_freq[m.emotion_label] = mood_freq.get(m.emotion_label, 0) + 1
            traits["recent_emotion"] = max(mood_freq, key=mood_freq.get)

        # 2. Habit streak strength
        habits = db.query(Habit).filter(Habit.user_id == user.id).all()
        high_streaks = [h for h in habits if h.streak_count and h.streak_count >= 3]
        traits["habit_streak"] = "high" if high_streaks else "low"

        # 3. Motivation detection
        last_3_days = datetime.utcnow() - timedelta(days=3)

        recent_journals = (
            db.query(JournalEntry)
            .filter(JournalEntry.user_id == user.id, JournalEntry.timestamp >= last_3_days)
            .count()
        )

        recent_checkins = (
            db.query(DailyCheckin)
            .filter(DailyCheckin.user_id == user.id, DailyCheckin.date >= func.date(last_3_days))
            .count()
        )

        recent_goals = (
            db.query(Goal)
            .filter(Goal.user_id == user.id, Goal.created_at >= last_3_days)
            .count()
        )

        total_entries = recent_journals + recent_checkins + recent_goals
        traits["motivation"] = "low" if total_entries <= 2 else "active"

        # 4. Tone suggestion
        if traits["recent_emotion"] in ["sadness", "fear", "anger"] or traits["habit_streak"] == "low":
            traits["tone"] = "calming"
        elif traits["recent_emotion"] in ["joy", "love"] and traits["habit_streak"] == "high":
            traits["tone"] = "energetic"

        # 5. Usage pattern
        traits["usage_pattern"] = analyze_usage_pattern(db, user)

        # ✅ Log traits
        bulk_log_traits(db, user, traits, source="persona_engine")
        logger.info(f"🔁 Persona traits updated for user {user.id}: {traits}")
        return traits

    except Exception as e:
        logger.warning(f"⚠️ Persona engine failed for user {user.id}: {e}")
        return traits


def analyze_usage_pattern(db: Session, user: User) -> str:
    """
    Returns a high-level behavior trait like:
    - goal_focused
    - habit_builder
    - reflective
    - seeker
    """
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)

    goal_count = db.query(Goal).filter(Goal.user_id == user.id).count()
    recent_goals = db.query(Goal).filter(Goal.user_id == user.id, Goal.created_at >= week_ago).count()

    habits = db.query(Habit).filter(Habit.user_id == user.id).all()
    active_habits = [h for h in habits if h.streak_count and h.streak_count >= 3]

    journals = (
        db.query(JournalEntry)
        .filter(JournalEntry.user_id == user.id, JournalEntry.timestamp >= week_ago)
        .count()
    )

    checkins = (
        db.query(DailyCheckin)
        .filter(DailyCheckin.user_id == user.id, DailyCheckin.date >= func.date(week_ago))
        .count()
    )

    info_msgs = (
        db.query(Message)
        .filter(
            Message.user_id == user.id,
            Message.sender == "user",
            Message.timestamp >= week_ago,
            (
                Message.message.ilike("%who%")
                | Message.message.ilike("%what%")
                | Message.message.ilike("%when%")
                | Message.message.ilike("%search%")
            ),
        )
        .count()
    )

    if goal_count >= 3 and recent_goals >= 2:
        return "goal_focused"
    elif len(active_habits) >= 2:
        return "habit_builder"
    elif (journals + checkins) >= 3:
        return "reflective"
    elif info_msgs >= 3:
        return "seeker"
    else:
        return "general"
