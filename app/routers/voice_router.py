# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, Request, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from app.models.database import SessionLocal
from app.models.user import User, TierLevel
from app.models.message_model import Message
from app.models.generated_audio import GeneratedAudio
from app.utils.audio_processor import transcribe_audio, synthesize_voice
from app.utils.ai_engine import generate_ai_reply
from app.utils.auth_utils import require_token, ensure_token_user_match, build_chat_history
from app.utils.tier_logic import get_monthly_limit
import os
import uuid
import mimetypes

from app.utils.rate_limit_utils import get_tier_limit, limiter
from app.schemas.intent_schemas import IntentRequest
from app.services.intent_router_core import detect_and_route_intent, IntentRequest

from app.utils.red_flag_utils import detect_red_flag
from app.utils.prompt_templates import red_flag_response, creator_info_response

from app.services.emotion_tone_updater import update_emotion_status



router = APIRouter()
ASSISTANT_NAME = "Neura"

# ---------------------- DB SESSION ----------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------- VOICE CHAT ENDPOINT ----------------------

@router.post("/voice-chat-with-neura")
@limiter.limit(get_tier_limit)
async def voice_chat_with_neura(
    request: Request,
    user_id: int = Form(...),
    conversation_id: int = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    """
    Accepts voice input, transcribes it, detects intent,
    and either respo-nds via fallback chat+TTS or routes to int-ent handler.
    """

    # ✅ Authentication
    ensure_token_user_match(user_data["sub"], user_id)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ✅ Validate MIME type file
    if file.content_type not in ["audio/wav", "audio/x-wav", "audio/mp3"]:
        raise HTTPException(status_code=400, detail="Invalid audio format. Use WAV or MP3.")

    # ✅ Tier limit logic
    monthly_limit = get_monthly_limit(user.tier)
    if user.tier == TierLevel.free:
        total_usage = user.monthly_gpt_count + user.monthly_voice_count
        if total_usage >= monthly_limit:
            return {
                "reply": f"⚠️ You've used your {monthly_limit} total messages this month. Upgrade your plan.",
                "memory_enabled": user.memory_enabled,
                "messages_used_this_month": total_usage,
                "messages_remaining": 0,
                "audio_url": None
            }
    else:
        if user.monthly_voice_count >= monthly_limit:
            return {
                "reply": f"⚠️ You've used your {monthly_limit} voice messages for {user.tier} this month.",
                "memory_enabled": user.memory_enabled,
                "messages_used_this_month": user.monthly_voice_count,
                "messages_remaining": 0,
                "audio_url": None
            }

    # ✅ Save file temporarily
    filename = f"temp_{uuid.uuid4()}.wav"
    filepath = os.path.join("/data/audio/temp_audio", filename)
    with open(filepath, "wb") as f:
        f.write(await file.read())

    # ✅ Transcribe
    try:
       transcript = transcribe_audio(filepath)
    finally:
       if os.path.exists(filepath):
          os.remove(filepath)

    # ✅ Update emotion
    emotion_label = await update_emotion_status(user, transcript, db)

    # 🚩 Red flag detection
    red_flag = detect_red_flag(transcript)
    if red_flag == "code":
        return {
            "reply": red_flag_response("code or internal details"),
            "memory_enabled": user.memory_enabled,
            "messages_used_this_month": user.monthly_voice_count,
            "messages_remaining": monthly_limit - user.monthly_voice_count,
            "audio_url": None
        }
    if red_flag == "creator":
        return {
            "reply": creator_info_response(),
            "memory_enabled": user.memory_enabled,
            "messages_used_this_month": user.monthly_voice_count,
            "messages_remaining": monthly_limit - user.monthly_voice_count,
            "audio_url": None
        }

    # ✅ Detect intent
    intent_prompt = f"""
    You are an assistant that classifies user intent.
    Return ONLY one word from this list:
    [
        journal, journal_list, journal_delete, journal_modify,
        checkin, checkin_list, checkin_delete, checkin_modify,
        habit, habit_list, habit_modify, habit_delete,
        goal, goal_list, goal_modify, goal_delete,
        search, notification, smart_reply,
        creator_mode, creator_caption, creator_content_ideas,
        creator_weekly_plan, creator_audience_helper, creator_viral_reels,
        creator_seo, creator_email, creator_time_planner,
        creator_youtube_script, creator_blog,
        fallback
    ]

    User input: {transcript}

    Intent:
    """
    intent_raw = generate_ai_reply(intent_prompt)
    intent = intent_raw.strip().lower()

    # ✅ If fallback, do chat
    if intent == "fallback":
        # Important tagging
        important_keywords = ["remember", "goal", "habit", "remind", "dream", "mission"]
        is_important = any(word in transcript.lower() for word in important_keywords)

        # Build chat history
        if user.memory_enabled:
            chat_history = build_chat_history(db, user.id, conversation_id=conversation_id or 1)
            full_prompt = f"{chat_history}\nUser: {transcript}\n{ASSISTANT_NAME}:"
        else:
            full_prompt = transcript

        # Generate reply
        assistant_reply = generate_ai_reply(full_prompt)

        # Synthesize voice
        voice_gender = user.voice if user.voice in ["male", "female"] else "male"

        # Audio output folders
        output_folder = "/data/audio/voice_chat"

        audio_output_path = synthesize_voice(assistant_reply, gender=voice_gender, output_folder=output_folder)

        # Save messages
        if user.memory_enabled:
            db.add_all([
                Message(
                    user_id=user.id,
                    conversation_id=conversation_id or 1,
                    sender="user",
                    message=transcript,
                    important=is_important
                ),
                Message(
                    user_id=user.id,
                    conversation_id=conversation_id or 1,
                    sender="assistant",
                    message=assistant_reply,
                    important=False
                ),
            ])

        # Save audio record
        generated_audio = GeneratedAudio(
            user_id=user.id,
            filename= os.path.join("voice_chat", os.path.basename(audio_output_path))
        )
        db.add(generated_audio)

        # Increment usage
        user.monthly_voice_count += 1
        db.commit()

        return {
            "reply": assistant_reply,
            "emotion": emotion_label,
            "memory_enabled": user.memory_enabled,
            "messages_used_this_month": user.monthly_voice_count,
            "messages_remaining": monthly_limit - user.monthly_voice_count,
            "audio_url": f"/get-voice-chat-audio?user_id={user.id}&filename={os.path.join('voice_chat', os.path.basename(audio_output_path))}"

        }

    # ✅ If intent is something else, call intent router
    else:
        # Emulate IntentRequest
        intent_payload = IntentRequest(
            user_id=user.id,
            message=transcript,
            conversation_id=conversation_id or 1
        )
        intent_result = await detect_and_route_intent(
            request=request,
            payload=intent_payload,
            db=db,
            user_data=user_data
        )

        return {
            **intent_result,
            "emotion": emotion_label
        }


# ---------------------- AUDIO STREAMING ENDPOINT ----------------------
class GetAudioRequest(BaseModel):
    user_id: int
    filename: str
@router.get("/get-voice-chat-audio")
@limiter.limit(get_tier_limit)
async def get_voice_chat_audio(
    payload: GetAudioRequest,
    request: Request,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    """
        Streams audio file back to client, supporting Range requests.
    """

    ensure_token_user_match(user_data["sub"], payload.user_id)

    # Validate file extension
    if not payload.filename.lower().endswith((".mp3", ".wav")):
        raise HTTPException(status_code=400, detail="Invalid file type.")

    audio_record = (
        db.query(GeneratedAudio)
        .filter(GeneratedAudio.user_id == payload.user_id)
        .filter(GeneratedAudio.filename == payload.filename)
        .first()
    )
    if not audio_record:
        raise HTTPException(status_code=404, detail="Audio not found or access denied")

    file_path = os.path.join("/data/audio", payload.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file missing on disk")

    file_size = os.path.getsize(file_path)
    content_type, _ = mimetypes.guess_type(file_path)
    content_type = content_type or "audio/mpeg"

    range_header = request.headers.get("range")
    if range_header:
        start = int(range_header.replace("bytes=", "").split("-")[0])
        end = file_size - 1
        length = end - start + 1
        with open(file_path, "rb") as f:
            f.seek(start)
            data = f.read(length)
        return StreamingResponse(
            iter([data]),
            status_code=206,
            media_type=content_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
            },
        )

    # Return file with extension
    return FileResponse(
        file_path,
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{os.path.basename(payload.filename)}"'
        }
    )

