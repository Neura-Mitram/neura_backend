# app/services/intent_handlers/intent_journal/handle_journal_list.py

from sqlalchemy.orm import Session
from app.models.user import User
from app.models.journal import JournalEntry
from app.utils.auth_utils import ensure_token_user_match
from fastapi import HTTPException

async def handle_journal_list(request: Request, user: User, message: str, db: Session):
    # Ensure token-user match
    await ensure_token_user_match(request, user.id)
    entries = db.query(JournalEntry).filter(JournalEntry.user_id == user.id).order_by(JournalEntry.timestamp.desc()).all()

    if not entries:
        raise HTTPException(status_code=404, detail="No journal entries found.")

    return {
        "message": f"📓 You have {len(entries)} journal entries.",
        "entries": [
            {
                "id": entry.id,
                "text": entry.entry_text,
                "ai_insight": entry.ai_insight,
                "timestamp": entry.timestamp.isoformat()
            }
            for entry in entries
        ]
    }
