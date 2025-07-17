# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.user import User
from app.models.habit import Habit
from app.models.goal import Goal
from app.models.journal import JournalEntry
from app.models.daily_checkin import DailyCheckin
from app.models.mood import MoodLog
import logging

logger = logging.getLogger(__name__)

def get_user_persona_snapshot(user: User, db: Session) -> dict:
    """
    Builds a lightweight persona snapshot for the given user from DB logs.
    Can be used to enrich AI prompts for contextual, personalized responses.
    """
    persona = {
        "goal_focus": user.goal_focus,
        "personality_mode": user.personality_mode,
        "emotion_status": user.emotion_status,
        "habit_streak": "unknown",
        "mood_trend": "unknown",
        "preferred_tone": "gentle"
    }

    try:
        # Analyze recent mood
        recent_moods = db.query(MoodLog).filter(
            MoodLog.user_id == user.id
        ).order_by(MoodLog.timestamp.desc()).limit(5).all()

        if recent_moods:
            mood_scores = {}
            for m in recent_moods:
                mood_scores[m.emotion_label] = mood_scores.get(m.emotion_label, 0) + 1
            sorted_moods = sorted(mood_scores.items(), key=lambda x: x[1], reverse=True)
            persona["mood_trend"] = sorted_moods[0][0]

        # Analyze habit consistency
        habits = db.query(Habit).filter(Habit.user_id == user.id).all()
        if habits:
            active_habits = [h for h in habits if h.current_streak and h.current_streak >= 3]
            persona["habit_streak"] = "high" if active_habits else "low"

        # Adjust tone suggestion using only supported emotion labels
        tone_map = {
            "joy": "energetic",
            "love": "energetic",
            "sadness": "calming",
            "fear": "calming",
            "anger": "grounded",
            "surprise": "balanced"
        }

        mood = persona.get("mood_trend", "")
        # Optional fallback: retain current tone if mood not in tone_map
        persona["preferred_tone"] = tone_map.get(mood, persona["preferred_tone"])

    except Exception as e:
        logger.warning(f"⚠️ Failed to build persona snapshot for user {user.temp_uid}: {e}")

    return persona
