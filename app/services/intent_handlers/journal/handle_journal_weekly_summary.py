# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from sqlalchemy.orm import Session
from fastapi import Request, HTTPException
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from app.models.journal import JournalEntry
from app.models.user import User
from app.utils.tier_logic import is_voice_ping_allowed
from app.utils.voice_sender import store_voice_weekly_summary
from app.utils.auth_utils import generate_ai_reply  # ✅ AI summary
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.usage_tracker import track_usage_event

async def handle_journal_weekly_summary(request: Request, user: User, message: str, db: Session):
    """
    Generates a weekly emotional summary from journal entries with AI insight.
    """
    today = datetime.utcnow().date()
    seven_days_ago = today - timedelta(days=6)

    entries = db.query(JournalEntry).filter(
        JournalEntry.user_id == user.id,
        JournalEntry.timestamp >= seven_days_ago
    ).all()

    if not entries:
        raise HTTPException(status_code=404, detail="No journal entries found in the last 7 days.")

    # Group by day
    daily_summary = defaultdict(lambda: defaultdict(int))  # {date: {emotion: count}}
    emotion_counter = Counter()

    for entry in entries:
        date_key = entry.timestamp.date().isoformat()
        emotion = entry.emotion_label or "love"
        daily_summary[date_key][emotion] += 1
        emotion_counter[emotion] += 1

    dominant_emotion = emotion_counter.most_common(1)[0][0] if emotion_counter else "love"

    # ✅ Generate AI insight based on emotion trend
    emotion_summary_text = "\n".join(
        f"{emotion}: {count} entries" for emotion, count in emotion_counter.items()
    )

    ai_prompt = f"""
You are Neura, the user's emotional assistant. Based on their journal entries over the past 7 days:

Dominant emotion: {dominant_emotion}
Emotion spread:
{emotion_summary_text}

Write a short, empathetic paragraph reflecting this emotional pattern. Use warmth and support. 
Close with a sentence like "Would you like a calming tip?" or "Want to explore this more?"
"""

    try:
        ai_insight = generate_ai_reply(inject_persona_into_prompt(user, ai_prompt, db))

    except Exception:
        ai_insight = "You've been processing a range of emotions this week. Just remember — every feeling is valid and healing takes time."

    # ✅ Voice nudge if eligible
    if is_voice_ping_allowed(user) and user.voice_nudges_enabled and user.preferred_delivery_mode == "voice":
        store_voice_weekly_summary(user, ai_insight, db)

    track_usage_event(db, user, category="journal_weekly_summary")

    return {
        "message": ai_insight,
        "dominant_emotion": dominant_emotion,
        "emotion_counts": dict(emotion_counter),
        "daily_summary": dict(daily_summary)
    }
