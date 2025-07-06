# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.user import User
from app.models.habit import Habit
from app.utils.auth_utils import ensure_token_user_match
from fastapi import HTTPException, Request

async def handle_list_habits(request: Request, user: User, message: str, db: Session):
    # Ensure token-user match
    # await ensure_token_user_match(request, user.id)
    habits = db.query(Habit).filter(Habit.user_id == user.id).order_by(Habit.created_at.desc()).all()

    return {
        "message": f"📋 You have {len(habits)} habit(s)",
        "habits": [
            {
                "id": h.id,
                "habit_name": h.habit_name,
                "frequency": h.frequency,
                "streak_count": h.streak_count,
                "last_completed": h.last_completed.isoformat() if h.last_completed else None
            } for h in habits
        ]
    }
