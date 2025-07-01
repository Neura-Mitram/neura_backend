# app/routers/event_router.py

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import SessionLocal
from app.models.user import User
from app.utils.auth_utils import require_token, ensure_token_user_match
from app.utils.voice_sender import send_voice_to_neura
import logging
import json
from app.utils.emotion_tone_updater import trigger_voice_if_keyword_matched

router = APIRouter()
logger = logging.getLogger(__name__)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class EventInput(BaseModel):
    user_id: int
    event_type: str  # e.g., "spotify_open", "gmail_open", "call_start"
    metadata: dict = {}  # Optional additional context

@router.post("/push/event")
async def handle_event_push(
    payload: EventInput,
    request: Request,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    # ✅ Check token-user match
    ensure_token_user_match(user_data["sub"], payload.user_id)

    # ✅ Load user
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 🔕 Skip if user preferences disable this feature
    if user.tier.value == "free" or not user.instant_alerts_enabled:
        return {"status": "skipped", "reason": "Free tier or realtime alerts disabled"}

    if user.preferred_delivery_mode != "voice":
        return {"status": "skipped", "reason": "User prefers text mode"}

    # ✅ Keyword-triggered voice notification
    keyword_result = await trigger_voice_if_keyword_matched(
        user=user,
        source=payload.event_type,
        content=json.dumps(payload.metadata or {}),
        db=db
    )

    # ✅ Normal event prompt
    emotion = user.emotion_status or "love"
    context = f"Context: {payload.metadata}" if payload.metadata else ""

    base_prompts = {
        "spotify_open": {
            "surprise": "Looks like you're diving into music. Anything on your mind?",
            "sadness": "Some music to relax? Take a deep breath. I'm here.",
            "love": "Music is a good escape. Be kind to yourself today.",
        },
        "gmail_open": {
            "surprise": "Checking your email? Hope it's all manageable!",
            "sadness": "Don't let work emails ruin your day. You're doing great.",
            "love": "Emails can wait. But your rest matters too.",
        },
        "call_start": {
            "surprise": "All the best for your call. Be confident!",
            "sadness": "Take it easy. You're in control.",
            "love": "Keep it short if you’re tired. You’ve got this.",
        },
        "calendar_open": {
            "surprise": "Let’s plan the day. Anything exciting coming up?",
            "sadness": "One thing at a time. You’ve got this.",
            "love": "Don’t overbook yourself. Energy is precious.",
        }
    }

    fallback_prompt = "You just interacted with your phone. How can I help today?"

    prompt_variants = base_prompts.get(payload.event_type, {})
    tone_prompt = prompt_variants.get(emotion, fallback_prompt)
    full_prompt = f"{tone_prompt} {context}".strip()

    logger.info(f"📲 Event trigger: {payload.event_type} | Emotion: {emotion} | User: {user.id}")

    try:
        result = await send_voice_to_neura(user.id, full_prompt)
        return {
            "status": "completed",
            "keyword_trigger": keyword_result,
            "event_trigger": {
                "prompt": full_prompt,
                "details": result
            }
        }
    except Exception as e:
        logger.error(f"❌ Voice send failed for user {user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to deliver voice event")