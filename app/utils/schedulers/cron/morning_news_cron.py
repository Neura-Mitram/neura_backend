# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from datetime import datetime
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.user import User
from app.utils.tier_logic import is_voice_ping_allowed
from app.services.search_service import search_duckduckgo, format_results_for_summary
from app.utils.ai_engine import generate_ai_reply
from app.utils.voice_sender import store_voice_weekly_summary
import logging

logger = logging.getLogger(__name__)

# ----------------------------
# Cron: Daily News Summary
# ----------------------------

def run_morning_news_cron():
    logger.info("[MorningNewsCron] Started at %s", datetime.utcnow())
    db = SessionLocal()

    try:
        users = db.query(User).filter(User.is_verified == True).all()
        for user in users:
            try:
                # Skip Free Tier unless upgraded later
                if user.tier == "free":
                    continue

                # Optional: Add flag in DB like user.morning_news_enabled
                # if not user.morning_news_enabled:
                #     continue

                # Get top news (DDG)
                results = search_duckduckgo("top news India today")
                if not results:
                    logger.warning("[MorningNewsCron] No results for user %s", user.id)
                    continue

                prompt = format_results_for_summary(results[:5], "today's top news in India")
                summary = generate_ai_reply(prompt).strip()

                # Optional: Weather alert injection
                if any(word in summary.lower() for word in ["rain", "storm", "heatwave"]):
                    summary = "☔️ Weather Alert: " + summary

                # Voice delivery
                if is_voice_ping_allowed(user) and user.voice_nudges_enabled and user.preferred_delivery_mode == "voice":
                    store_voice_weekly_summary(user, summary, db)
                    logger.info("[MorningNewsCron] Sent voice news to user %s", user.id)

            except Exception as e:
                logger.error("[MorningNewsCron] Error for user %s: %s", user.id, str(e))
                db.rollback()

    finally:
        db.close()
        logger.info("[MorningNewsCron] Completed")


# ----------------------------
# Utility: Detect Trivia-like Questions
# ----------------------------

def is_trivia_question(msg: str) -> bool:
    if not msg:
        return False
    msg = msg.lower().strip()
    if msg.endswith("?") or msg.startswith(("what", "who", "when", "where", "how", "why")):
        return True
    return False
