# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.user import User
from app.models.journal import JournalEntry
from fastapi import HTTPException, Request
from app.utils.ai_engine import generate_ai_reply
from app.utils.auth_utils import ensure_token_user_match
import json
from app.services.emotion_tone_updater import update_emotion_status
from app.utils.prompt_templates import journal_modify_prompt
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.usage_tracker import track_usage_event

async def handle_journal_modify(request: Request, user: User, message: str, db: Session):
    # Ensure token-user match
    # await ensure_token_user_match(request, user.id)

    # 🔍 Emotion Detection
    emotion_label = await update_emotion_status(user, message, db, source="journal_modify")

    prompt = journal_modify_prompt(message, emotion_label)

    try:
        parsed = json.loads(generate_ai_reply(inject_persona_into_prompt(user, prompt, db)))
        entry_id = parsed["entry_id"]
        new_text = parsed["new_text"]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse input: {e}")

    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id, JournalEntry.user_id == user.id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    entry.entry_text = new_text

    # ✨ Regenerate insight and update emotion
    new_prompt = f"""
    You are a compassionate assistant. The user is currently feeling: **{emotion_label}**.

    Reflect on the following updated journal entry and provide 2–3 sentences of helpful insight:
    "{new_text}"
    """
    entry.ai_insight = generate_ai_reply(inject_persona_into_prompt(user, new_prompt, db))
    entry.emotion_label = emotion_label

    db.commit()
    db.refresh(entry)
    track_usage_event(db, user, category="journal_modify")

    return {"message": f"✍️ Journal entry {entry_id} updated successfully."}
