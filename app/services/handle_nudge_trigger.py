# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import Request
from sqlalchemy.orm import Session
from app.services.nudge_service import generate_nudge_for_user
from app.utils.tier_logic import get_user_tier
from app.models.user import User
from app.utils.usage_tracker import track_usage_event  # Optional logging
import logging

logger = logging.getLogger(__name__)

async def handle_nudge_trigger(request: Request, user: User, message: str, db: Session):
    tier = get_user_tier(user)

    if tier == "free":
        return {
            "type": "nudge",
            "message": "Nudges are available for Basic and Pro users only."
        }

    try:
        nudge_text = await generate_nudge_for_user(user, db)
    except Exception as e:
        logger.warning(f"⚠️ Nudge generation failed: {e}")
        nudge_text = "I'm here if you need a little push or support. 💡"

    try:
        await track_usage_event(db, user, category="nudge_manual")
    except Exception as e:
        logger.warning(f"⚠️ Failed to track nudge usage: {e}")

    return {
        "type": "nudge",
        "nudge": nudge_text
    }