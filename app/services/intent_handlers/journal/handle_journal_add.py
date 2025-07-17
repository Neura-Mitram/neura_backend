# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.user import User
from app.models.journal import JournalEntry
from app.utils.ai_engine import generate_ai_reply
from app.utils.auth_utils import ensure_token_user_match
from datetime import datetime
from fastapi import HTTPException, Request
from app.services.emotion_tone_updater import update_emotion_status
from app.utils.prompt_templates import journal_add_prompt
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.usage_tracker import track_usage_event

async def handle_journal_add(request: Request, user: User, message: str, db: Session):

    """
    Saves a journal entry for the user and generates AI insight using Mistral.
    Encrypted version using hybrid properties.
    """
    try:

        # 🔍 Emotion Detection
        emotion_label = await update_emotion_status(user, message, db, source="journal_add")

        # 🔍 Mistral prompt to generate reflective insight
        prompt = journal_add_prompt(message, emotion_label)

        ai_insight = generate_ai_reply(inject_persona_into_prompt(user, prompt, db))

        new_entry = JournalEntry(
            user_id=user.id,
            entry_text=message,
            ai_insight=ai_insight,
            timestamp=datetime.utcnow(),
            emotion_label=emotion_label
        )
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
        track_usage_event(db, user, category="journal_add")

        return {
            "message": "📝 Journal entry saved.",
            "journal": {
                "entry_text": new_entry.entry_text,
                "ai_insight": new_entry.ai_insight,
                "timestamp": new_entry.timestamp.isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to save journal entry: {e}")
