# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import Request
from sqlalchemy.orm import Session
from app.services.nudge_service import generate_nudge_for_user
from app.utils.tier_logic import get_user_tier
from app.models.user import User

async def handle_nudge_trigger(request: Request, user: User, message: str, db: Session):
    tier = get_user_tier(user)
    if tier == "free":
        return {
            "type": "nudge",
            "message": "Nudges are available for Basic and Pro users only."
        }

    # Reuse same logic used in cron nudge
    nudge_text = generate_nudge_for_user(user, db)

    return {
        "type": "nudge",
        "nudge": nudge_text
    }
