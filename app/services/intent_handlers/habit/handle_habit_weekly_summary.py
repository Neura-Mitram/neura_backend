# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from datetime import datetime, timedelta
from fastapi import Request
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.habit import Habit
from app.utils.ai_engine import generate_ai_reply
from app.utils.prompt_templates import habit_summary_prompt, habit_recommender_prompt
from app.utils.voice_sender import store_voice_weekly_summary
from app.utils.tier_logic import is_voice_ping_allowed
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.usage_tracker import track_usage_event


async def handle_habit_weekly_summary(request: Request, user: User, message: str, db: Session):
    """
    Weekly summary of user's habit performance with AI-generated motivational insight
    and specific feedback on missed habits.
    """
    week_ago = datetime.utcnow() - timedelta(days=7)
    habits = db.query(Habit).filter(Habit.user_id == user.id, Habit.status == "active").all()

    completed = []
    missed = []
    streaks = []
    feedback_lines = []

    for h in habits:
        if h.last_completed and h.last_completed >= week_ago:
            completed.append(h)
            if h.streak_count >= 2:
                streaks.append(h)
        else:
            missed.append(h)
            last_done = h.last_completed.strftime('%b %d') if h.last_completed else "never"
            feedback_lines.append(
                f"⚠️ You’re slipping on *{h.habit_name}* – last done {last_done}. Want to restart your streak?"
            )

    plain_summary = f"""
🧠 Weekly Habit Summary

✅ Completed: {len(completed)} habits
⚠️ Missed: {len(missed)} habits
🔥 Streaks: {len(streaks)} habits

Completed: {[h.habit_name for h in completed]}
Missed: {[h.habit_name for h in missed]}
Streaks: {[h.habit_name for h in streaks]}
    """

    # 🎯 AI Insight
    try:
        ai_prompt = habit_summary_prompt(completed, missed, streaks)
        ai_reply = generate_ai_reply(inject_persona_into_prompt(user, ai_prompt, db))

    except Exception:
        ai_reply = "(AI summary unavailable)"

    # 🌱 Habit Recommender
    try:
        recommend_prompt = habit_recommender_prompt(user.name, completed, missed, streaks)
        habit_suggestions = generate_ai_reply(inject_persona_into_prompt(user, recommend_prompt, db))
    except Exception:
        habit_suggestions = "(No new suggestions available)"

    # 🎧 Voice Summary (Proactive Nudge)
    if is_voice_ping_allowed(user) and user.voice_nudges_enabled and user.preferred_delivery_mode == "voice":
        full_summary_text = ai_reply if ai_reply and ai_reply != "(AI summary unavailable)" else plain_summary
        store_voice_weekly_summary(user, full_summary_text, db)

    track_usage_event(db, user, category="habit_weekly_summary")

    return {
        "message": "🧘 Here's your weekly habit reflection",
        "summary": plain_summary,
        "ai_summary": ai_reply,
        "habit_feedback": feedback_lines,  # ✅ Personalized habit feedback
        "habit_suggestions": habit_suggestions  # ✅ AI suggestions
    }
