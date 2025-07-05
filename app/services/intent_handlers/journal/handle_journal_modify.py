# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.user import User
from app.models.journal import JournalEntry
from fastapi import HTTPException, Request
from app.services.mistral_ai_service import get_mistral_reply
from app.utils.auth_utils import ensure_token_user_match
import json
from app.services.emotion_tone_updater import update_emotion_status
from app.utils.prompt_templates import journal_modify_prompt

async def handle_journal_modify(request: Request, user: User, message: str, db: Session):
    # Ensure token-user match
    await ensure_token_user_match(request, user.id)

    # 🔍 Emotion Detection
    emotion_label = await update_emotion_status(user, message, db)

    prompt = journal_modify_prompt(message, emotion_label)

    try:
        parsed = json.loads(get_mistral_reply(prompt))
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
    entry.ai_insight = get_mistral_reply(new_prompt)
    entry.emotion_label = emotion_label

    db.commit()

    return {"message": f"✍️ Journal entry {entry_id} updated successfully."}
