from sqlalchemy.orm import Session
from app.models.user import User
from app.models.daily_checkin import DailyCheckin
from app.services.mistral_ai_service import get_mistral_reply
from app.utils.auth_utils import ensure_token_user_match
from fastapi import HTTPException, Request
import json
from app.utils.prompt_templates import checkin_delete_prompt

async def handle_checkin_delete(request, user: User, message: str, db: Session):
    await ensure_token_user_match(request, user.id)
    """
    Uses Mistral to identify the check-in ID or date to delete.
    """
    prompt = checkin_delete_prompt(message)

    mistral_response = get_mistral_reply(prompt)

    try:
        parsed = json.loads(mistral_response)
        checkin = None

        if parsed.get("checkin_id"):
            checkin = db.query(DailyCheckin).filter_by(id=parsed["checkin_id"], user_id=user.id).first()
        elif parsed.get("date"):
            from datetime import datetime
            target_date = datetime.strptime(parsed["date"], "%Y-%m-%d").date()
            checkin = db.query(DailyCheckin).filter_by(user_id=user.id, date=target_date).first()

        if not checkin:
            raise HTTPException(status_code=404, detail="No matching check-in found.")

        db.delete(checkin)
        db.commit()

        return {"message": f"🗑️ Check-in deleted for {checkin.date.isoformat()}"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"🛑 Failed to delete check-in: {e}")
