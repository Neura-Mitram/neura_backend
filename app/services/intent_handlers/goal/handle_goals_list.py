# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.user import User
from app.models.goal import Goal
from app.utils.auth_utils import ensure_token_user_match
from fastapi import HTTPException, Request

async def handle_list_goals(request: Request, user: User, message: str, db: Session):
    # Ensure token-user match
    # await ensure_token_user_match(request, user.id)
    """
    Returns all goal entries for the user.
    """
    goals = db.query(Goal).filter(Goal.user_id == user.id).order_by(Goal.created_at.desc()).all()

    if not goals:
        return {"message": "📭 No goals found."}

    return {
        "message": "🎯 Your goals:",
        "goals": [
            {
                "id": goal.id,
                "goal_text": goal.goal_text,
                "ai_insight": goal.ai_insight,
                "deadline": goal.deadline.isoformat() if goal.deadline else None,
                "status": goal.status,
                "created_at": goal.created_at.isoformat()
            }
            for goal in goals
        ]
    }
