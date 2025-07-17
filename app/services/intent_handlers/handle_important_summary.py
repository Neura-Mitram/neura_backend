# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from fastapi import Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.utils.ai_engine import generate_ai_reply
from app.models.message_model import Message
from app.models.user import User
from app.utils.tier_logic import get_important_summary_limit, has_emotion_insight, is_voice_ping_allowed
from app.utils.voice_sender import store_voice_weekly_summary  # ✅ Added for voice logging
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.usage_tracker import track_usage_event

async def handle_important_summary(request: Request, user: User, message: str, db: Session):
    """
    Summarizes the most important things user said recently using memory flag.
    """

    one_week_ago = datetime.utcnow() - timedelta(days=7)

    limit = get_important_summary_limit(user.tier)
    allow_emotion = has_emotion_insight(user.tier)

    messages = (
        db.query(Message)
        .filter(Message.user_id == user.id)
        .filter(Message.important == True)
        .filter(Message.timestamp >= one_week_ago)
        .order_by(Message.timestamp)
        .limit(limit)
        .all()
    )
    messages.reverse()

    if not messages:
        return {"message": "You haven't marked anything important in the past week."}

    combined = "\n".join(f"- {m.message}" for m in messages)

    prompt = f"""
You are Neura, the user's AI assistant. Summarize the most important things the user shared in the past week.

Each message may contain an emotion (e.g., sadness, joy, anger, fear, love, surprise).
Use this to reflect the emotional tone in your summary.

Messages:
{combined}

Summary (with emotional insight):
"""
    if allow_emotion:
        prompt += "\nAlso infer their emotional tone based on these messages."

    prompt += "\n\nSummary:\n"

    final_prompt = inject_persona_into_prompt(user, prompt, db)
    ai_response = generate_ai_reply(final_prompt).strip()


    # ✅ Proactive voice nudge if eligible
    if is_voice_ping_allowed(user) and user.voice_nudges_enabled and user.preferred_delivery_mode == "voice":
        store_voice_weekly_summary(user, ai_response, db)

    track_usage_event(db, user, category="important_summary")

    return {"message": ai_response}
