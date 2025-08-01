# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.goal import Goal
from app.models.user import User
from app.utils.ai_engine import generate_ai_reply
from app.utils.auth_utils import ensure_token_user_match
from fastapi import HTTPException, Request
import json
from app.utils.prompt_templates import goal_delete_prompt
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt


async def handle_delete_goal(request: Request, user: User, message: str, db: Session):
    # Ensure token-user match
    # await ensure_token_user_match(request, user.id)
    """
    Uses Mistral to extract goal_id to delete.
    """

    prompt = goal_delete_prompt(message)

    mistral_response = generate_ai_reply(inject_persona_into_prompt(user, prompt, db))

    try:
        parsed = json.loads(mistral_response)
        goal_id = parsed["goal_id"]

        goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")

        db.delete(goal)
        db.commit()
        db.refresh(goal)

        return {"message": f"🗑️ Goal ID {goal_id} deleted."}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete goal: {e}")
