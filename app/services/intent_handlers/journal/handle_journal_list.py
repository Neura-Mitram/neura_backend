# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.user import User
from app.models.journal import JournalEntry
from fastapi import HTTPException, Request
import re

async def handle_journal_list(request: Request, user: User, message: str, db: Session):
    """
    Lists journal entries, optionally filtered by emotion.
    """
    # Step 1: Extract emotion from the message if present
    emotion_filter = extract_emotion_filter(message)

    # Step 2: Query journal entries
    query = db.query(JournalEntry).filter(JournalEntry.user_id == user.id)
    if emotion_filter:
        query = query.filter(JournalEntry.emotion_label.ilike(f"%{emotion_filter}%"))

    entries = query.order_by(JournalEntry.timestamp.desc()).all()

    if not entries:
        raise HTTPException(status_code=404, detail="No matching journal entries found.")

    return {
        "message": f"📓 Found {len(entries)} journal entries"
                   + (f" with emotion: {emotion_filter}" if emotion_filter else ""),
        "entries": [
            {
                "id": entry.id,
                "text": entry.entry_text,
                "ai_insight": entry.ai_insight,
                "emotion": entry.emotion_label,
                "timestamp": entry.timestamp.isoformat()
            }
            for entry in entries
        ]
    }

def extract_emotion_filter(text: str):
    """
    Very simple match: looks for common emotion words in the user's message.
    """
    emotions = ["sad", "happy", "angry", "anxious", "calm", "neutral", "tired", "excited"]
    text = text.lower()
    for emotion in emotions:
        if re.search(rf"\b{emotion}\b", text):
            return emotion
    return None
