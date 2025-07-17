# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.user_persona_utils import get_user_persona_snapshot
from app.utils.tone_bias_helper import generate_tone_instruction


def inject_persona_into_prompt(user: User, raw_prompt: str, db: Session) -> str:
    """
    Injects user persona tone, emotion, behavior, and usage pattern modifiers into the prompt.
    This version supports advanced prompt shaping for Mistral.
    """

    persona = get_user_persona_snapshot(user, db)
    tone_instruction = generate_tone_instruction(persona)

    persona_header = f"""
[User Persona Summary]
- Emotion: {persona.get("emotion_status", "unknown")}
- Mood Trend: {persona.get("mood_trend", "unknown")}
- Personality Mode: {persona.get("personality_mode", "neutral")}
- Goal Focus: {persona.get("goal_focus", "general")}
- Habit Streak: {persona.get("habit_streak", "unknown")}
- Usage Pattern: {persona.get("usage_pattern", "unknown")}

[Assistant Style Guide]
{tone_instruction}

---

"""

    return f"{persona_header}{raw_prompt}"
