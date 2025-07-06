# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.user import User
from app.models.habit import Habit
from app.services.mistral_ai_service import get_mistral_reply
from app.utils.auth_utils import ensure_token_user_match
from fastapi import HTTPException, Request
import json
from app.utils.prompt_templates import habit_delete_prompt

async def handle_delete_habit(request: Request, user: User, message: str, db: Session):
    # Ensure token-user match
    # await ensure_token_user_match(request, user.id)
    """
    Uses Mistral to extract the habit_id to delete.
    """
    prompt = habit_delete_prompt(message)

    try:
        response = get_mistral_reply(prompt)
        data = json.loads(response)
        habit = db.query(Habit).filter(Habit.id == data["habit_id"]).first()

        if not habit or habit.user_id != user.id:
            raise HTTPException(status_code=404, detail="Habit not found or unauthorized")

        db.delete(habit)
        db.commit()

        return {"message": "🗑️ Habit deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"🛑 Failed to delete habit: {e}")
