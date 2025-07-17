# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.user import User
from app.models.journal import JournalEntry
from fastapi import HTTPException
from app.utils.ai_engine import generate_ai_reply
from app.utils.auth_utils import ensure_token_user_match
import json
from app.utils.prompt_templates import journal_delete_prompt
from fastapi import Request
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt

async def handle_journal_delete(request: Request, user: User, message: str, db: Session):
    # Ensure token-user match
    # await ensure_token_user_match(request, user.id)

    prompt = journal_delete_prompt(message)

    try:
        parsed = json.loads(generate_ai_reply(inject_persona_into_prompt(user, prompt, db)))
        entry_id = parsed["entry_id"]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract entry ID: {e}")

    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id, JournalEntry.user_id == user.id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    db.delete(entry)
    db.commit()
    db.refresh(entry)

    return {"message": f"🗑️ Journal entry {entry_id} deleted successfully."}
