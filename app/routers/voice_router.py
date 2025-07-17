# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.
# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
import os, uuid

from app.models.database import SessionLocal
from app.models.user import User, TierLevel
from app.models.message_model import Message
# from app.models.generated_audio import GeneratedAudio
from app.utils.audio_processor import transcribe_audio, synthesize_voice, transcribe_audio_bytes
from app.utils.auth_utils import require_token, ensure_token_user_match, build_chat_history
from app.utils.ai_engine import generate_ai_reply
from app.utils.tier_logic import get_monthly_limit
from app.utils.red_flag_utils import detect_red_flag, SEVERE_KEYWORDS
from app.utils.prompt_templates import red_flag_response, creator_info_response, self_query_response
from app.utils.rate_limit_utils import get_tier_limit, limiter
from app.schemas.intent_schemas import IntentRequest
from app.services.intent_router_core import detect_and_route_intent
from app.services.emotion_tone_updater import update_emotion_status
from app.services.persona_engine import run_persona_engine
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.models.sos_contact import SOSContact
from app.services.translation_service import translate  # ✅ NEW
from app.services.handle_interpreter_mode import handle_interpreter_mode
from app.services.handle_ambient_mode import handle_ambient_mode

router = APIRouter()
ASSISTANT_NAME = "Neura"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/voice-chat-with-neura")
@limiter.limit(get_tier_limit)
async def voice_chat_with_neura(
    request: Request,
    device_id: str = Form(...),
    conversation_id: int = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], device_id)
    user = db.query(User).filter(User.temp_uid == device_id).first()

    # ✅ Wakeword enforcement
    if not os.path.exists(f"trained_models/{device_id}_neura.tflite"):
        return {
            "reply": "🔒 Please complete your wakeword setup to activate Neura.",
            "require_wakeword": True,
            "audio_stream_url": None,
            "messages_used_this_month": user.monthly_voice_count,
            "messages_remaining": get_monthly_limit(user.tier) - user.monthly_voice_count,
        }

    # ✅ SOS contact check
    if not db.query(SOSContact).filter(SOSContact.device_id == device_id).first():
        return {
            "reply": "🛡️ Please add an SOS contact to continue. This is required for your safety.",
            "require_sos_contact": True
        }

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if file.content_type not in ["audio/wav", "audio/x-wav", "audio/mp3"]:
        raise HTTPException(status_code=400, detail="Invalid audio format. Use WAV or MP3.")

    # ✅ Rate limiting
    monthly_limit = get_monthly_limit(user.tier)
    total_usage = user.monthly_gpt_count + user.monthly_voice_count
    if user.tier == TierLevel.free and total_usage >= monthly_limit:
        return {
            "reply": f"⚠️ You've used your {monthly_limit} messages this month.",
            "memory_enabled": user.memory_enabled,
            "messages_used_this_month": total_usage,
            "messages_remaining": 0,
            "audio_stream_url": None
        }
    if user.tier != TierLevel.free and user.monthly_voice_count >= monthly_limit:
        return {
            "reply": f"⚠️ You've used your {monthly_limit} voice messages this month.",
            "memory_enabled": user.memory_enabled,
            "messages_used_this_month": user.monthly_voice_count,
            "messages_remaining": 0,
            "audio_stream_url": None
        }

    # ✅ Transcribe in-memory audio
    audio_bytes = await file.read()
    transcript = transcribe_audio_bytes(audio_bytes)

    if user.active_mode == "ambient":
        return await handle_ambient_mode(user, transcript, db)

    return await process_voice_input(
        transcript=transcript,
        user=user,
        db=db,
        request=request,
        conversation_id=conversation_id or 1,
        monthly_limit=monthly_limit
    )


async def process_voice_input(
    transcript: str,
    user: User,
    db: Session,
    request: Request = None,
    conversation_id: int = 1,
    monthly_limit: int = 100
) -> dict:

    user_lang = user.preferred_lang or "en"
    if user_lang != "en":
        transcript = translate(transcript, source_lang=user_lang, target_lang="en")

    # ✅ Speaker mode toggle
    if "say this aloud" in transcript.lower() or "switch to speaker" in transcript.lower():
        user.output_audio_mode = "speaker"
        db.commit()
        return {
            "reply": "🔊 Speaker mode enabled. I'll speak out loud now.",
            "audio_stream_url": synthesize_voice("Speaker mode enabled. I'll speak out loud now.", gender=user.voice, emotion="joy", lang=user_lang)
        }

    if "turn off speaker" in transcript.lower() or "be silent" in transcript.lower():
        user.output_audio_mode = "silent"
        db.commit()
        return {
            "reply": "🔇 Silent mode activated. I'll respond quietly.",
            "audio_stream_url": synthesize_voice("Silent mode activated. I'll respond quietly.", gender=user.voice, emotion="neutral", lang=user_lang)
        }

    # ✅ Handle interpreter toggle
    if "start interpreter" in transcript.lower():
        user.active_mode = "interpreter"
        db.commit()
        return {
            "reply": "🟢 Interpreter mode activated.",
            "audio_stream_url": synthesize_voice("Interpreter mode activated.", gender=user.voice, emotion="joy", lang=user_lang),
            "memory_enabled": user.memory_enabled,
            "messages_used_this_month": user.monthly_voice_count,
            "messages_remaining": monthly_limit - user.monthly_voice_count
        }

    if "stop interpreter" in transcript.lower():
        user.active_mode = None
        db.commit()
        return {
            "reply": "🛑 Interpreter mode deactivated.",
            "audio_stream_url": synthesize_voice("Interpreter mode turned off.", gender=user.voice, emotion="unknown", lang=user_lang),
            "memory_enabled": user.memory_enabled,
            "messages_used_this_month": user.monthly_voice_count,
            "messages_remaining": monthly_limit - user.monthly_voice_count
        }

    # ✅ Handle interpreter mode
    if user.active_mode == "interpreter":
        return await handle_interpreter_mode(request, user, transcript, db)

    # ✅ Normal flow: emotion, intent, etc.
    is_important = any(word in transcript.lower() for word in ["goal", "habit", "remind", "dream", "mission"])
    emotion_label = await update_emotion_status(user, transcript, db, source="voice_chat")
    await run_persona_engine(db, user)

       # ✅ Red flag detection
    red_flag = detect_red_flag(transcript)

    # Internal system/code queries
    if red_flag == "code":
        reply_text = red_flag_response(reason="code or internal details", lang=user_lang)
        return {
            "reply": reply_text,
            "memory_enabled": user.memory_enabled,
            "messages_used_this_month": user.monthly_voice_count,
            "messages_remaining": monthly_limit - user.monthly_voice_count,
            "audio_stream_url": synthesize_voice(
                text=reply_text,
                gender=user.voice or "female",
                emotion="unknown",
                lang=user_lang
            )
        }

    # Creator-related queries
    if red_flag == "creator":
        reply_text = creator_info_response(lang=user_lang)
        return {
            "reply": reply_text,
            "memory_enabled": user.memory_enabled,
            "messages_used_this_month": user.monthly_voice_count,
            "messages_remaining": monthly_limit - user.monthly_voice_count,
            "audio_stream_url": synthesize_voice(
                text=reply_text,
                gender=user.voice or "female",
                emotion="surprise",
                lang=user_lang
            )
        }

    # Self-descriptive onboarding queries
    if red_flag == "self_query":
        reply_text = self_query_response(ai_name=user.ai_name or "Neura", lang=user_lang)
        return {
            "reply": reply_text,
            "memory_enabled": user.memory_enabled,
            "messages_used_this_month": user.monthly_voice_count,
            "messages_remaining": monthly_limit - user.monthly_voice_count,
            "audio_stream_url": synthesize_voice(
                text=reply_text,
                gender=user.voice or "female",
                emotion="joy",
                lang=user_lang
            )
        }

    # SOS trigger phrases
    if red_flag == "sos":
        is_force = any(term in transcript.lower() for term in SEVERE_KEYWORDS)
        reply_text = "🚨 Emergency detected. Triggering SOS alert."
        return {
            "reply": reply_text,
            "trigger_sos": True,
            "trigger_sos_force": is_force,
            "memory_enabled": user.memory_enabled,
            "messages_used_this_month": user.monthly_voice_count,
            "messages_remaining": monthly_limit - user.monthly_voice_count,
            "audio_stream_url": synthesize_voice(
                text=reply_text,
                gender=user.voice or "female",
                emotion="fear",
                lang=user_lang
            )
        }

    # ✅ Intent detection
    intent_prompt = f"""
    You are an assistant that classifies user intent.
    Return ONLY one word from this list:
    [journal, journal_list, journal_delete, journal_modify,
     checkin, checkin_list, checkin_delete, checkin_modify,
     habit, habit_list, habit_modify, habit_delete,
     goal, goal_list, goal_modify, goal_delete,
     search, notification, smart_reply,
     creator_mode, creator_caption, creator_content_ideas,
     creator_weekly_plan, creator_audience_helper, creator_viral_reels,
     creator_seo, creator_email, creator_time_planner,
     creator_youtube_script, creator_blog,
     fallback]
    User input: {transcript}
    Intent:
    """
    intent = generate_ai_reply(inject_persona_into_prompt(user, intent_prompt, db)).strip().lower()

    if intent == "fallback":
        if user.memory_enabled:
            history = build_chat_history(db, user.id, conversation_id=conversation_id)
            prompt = f"{history}User: {transcript}\n{ASSISTANT_NAME}:"
        else:
            prompt = f"User: {transcript}\n{ASSISTANT_NAME}:"

        assistant_reply = generate_ai_reply(inject_persona_into_prompt(user, prompt, db))

        if user_lang != "en":
            assistant_reply = translate(assistant_reply, source_lang="en", target_lang=user_lang)

        audio_stream_url = synthesize_voice(
            text=assistant_reply,
            gender=user.voice if user.voice in ["male", "female"] else "male",
            emotion=emotion_label,
            lang=user_lang
        )

        if user.memory_enabled:
            db.add_all([
                Message(user_id=user.id, conversation_id=conversation_id, sender="user", message=transcript, important=is_important),
                Message(user_id=user.id, conversation_id=conversation_id, sender="assistant", message=assistant_reply, important=False)
            ])
        user.monthly_voice_count += 1
        db.commit()

        return {
            "reply": assistant_reply,
            "emotion": emotion_label,
            "memory_enabled": user.memory_enabled,
            "messages_used_this_month": user.monthly_voice_count,
            "messages_remaining": monthly_limit - user.monthly_voice_count,
            "important": is_important,
            "audio_stream_url": audio_stream_url
        }

    # ✅ All other intents
    intent_result = await detect_and_route_intent(
        request=request,
        payload=IntentRequest(user_id=user.id, message=transcript, conversation_id=conversation_id),
        db=db,
        user_data={"sub": user.temp_uid}
    )

    if user_lang != "en" and "reply" in intent_result:
        intent_result["reply"] = translate(intent_result["reply"], source_lang="en", target_lang=user_lang)

    if "reply" in intent_result:
        intent_result["audio_stream_url"] = synthesize_voice(
            text=intent_result["reply"],
            gender=user.voice,
            emotion=emotion_label,
            lang=user_lang
        )
        user.monthly_voice_count += 1
        db.commit()

    return {
        **intent_result,
        "emotion": emotion_label,
        "memory_enabled": user.memory_enabled,
        "messages_used_this_month": user.monthly_voice_count,
        "messages_remaining": monthly_limit - user.monthly_voice_count,
        "important": is_important
    }


@router.post("/toggle-interpreter-mode")
async def toggle_interpreter_mode(
    device_id: str = Form(...),
    enable: bool = Form(...),
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], device_id)
    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.active_mode = "interpreter" if enable else None
    db.commit()

    return {
        "success": True,
        "active_mode": user.active_mode,
        "message": "Interpreter mode " + ("enabled" if enable else "disabled")
    }
