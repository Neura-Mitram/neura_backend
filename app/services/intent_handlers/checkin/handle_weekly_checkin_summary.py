# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from collections import defaultdict
from app.models.daily_checkin import DailyCheckin
from app.models.user import User
from app.utils.auth_utils import generate_ai_reply
from app.utils.tier_logic import is_voice_ping_allowed
from app.utils.voice_sender import store_voice_weekly_summary  # ✅ added voice nudge
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.usage_tracker import track_usage_event

def format_emotion_pattern(summary):
    lines = []
    for emotion, days in summary.items():
        day_str = ", ".join(days)
        lines.append(f"- {emotion}: {day_str}")
    return "\n".join(lines)

async def handle_weekly_checkin_summary(request: Request, user: User, message: str, db: Session):
    """
    Analyzes user's last 7 days of check-ins and returns emotion summary.
    """
    past_week = datetime.utcnow().date() - timedelta(days=7)

    entries = db.query(DailyCheckin).filter(
        DailyCheckin.user_id == user.id,
        DailyCheckin.date >= past_week
    ).all()

    if not entries:
        return {
            "message": "No check-in data found for the past week."
        }

    emotion_summary = defaultdict(list)
    for entry in entries:
        label = entry.emotion_label or "neutral"
        day = entry.date.strftime("%A")
        emotion_summary[label].append(day)

    formatted_pattern = format_emotion_pattern(emotion_summary)

    prompt = f"""
Neura is summarizing the user's emotional check-in pattern.

Here is the pattern over the last 7 days:
{formatted_pattern}

Write a gentle, empathetic paragraph reflecting the pattern.
End with a warm suggestion like “Want to add something?” or “Need a tip for next week?”
    """

    try:
        reply = generate_ai_reply(inject_persona_into_prompt(user, prompt, db))

    except Exception:
        reply = "Here's a reflection on your emotions this week. You’ve done your best, and that matters."

    # ✅ Voice nudge if allowed
    if is_voice_ping_allowed(user) and user.voice_nudges_enabled and user.preferred_delivery_mode == "voice":
        store_voice_weekly_summary(user, reply, db)

    track_usage_event(db, user, category="checkin_weekly_summary")

    return {
        "message": reply,
        "raw_pattern": emotion_summary
    }
