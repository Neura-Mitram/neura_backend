# app/services/intent_handlers/intent_journal/handle_journal_delete.py

from sqlalchemy.orm import Session
from app.models.user import User
from app.models.journal import JournalEntry
from fastapi import HTTPException
from app.services.mistral_ai_service import get_mistral_reply
from app.utils.auth_utils import ensure_token_user_match
import json
from app.utils.prompt_templates import journal_delete_prompt

async def handle_journal_delete(request: Request, user: User, message: str, db: Session):
    # Ensure token-user match
    await ensure_token_user_match(request, user.id)

    prompt = journal_delete_prompt(message)

    try:
        parsed = json.loads(get_mistral_reply(prompt))
        entry_id = parsed["entry_id"]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract entry ID: {e}")

    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id, JournalEntry.user_id == user.id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    db.delete(entry)
    db.commit()

    return {"message": f"🗑️ Journal entry {entry_id} deleted successfully."}
