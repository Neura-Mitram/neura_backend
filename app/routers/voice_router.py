from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from app.models.database import SessionLocal
from app.models.user_model import User, TierLevel
from app.models.message_model import Message
from app.models.generated_audio_model import GeneratedAudio
from app.utils.audio_processor import transcribe_audio, synthesize_voice
from app.utils.ai_engine import generate_ai_reply
from app.utils.auth_utils import require_token, ensure_token_user_match
from app.utils.tier_check import get_monthly_limit
import os
import uuid
import mimetypes


from app.utils.rate_limit_utils import get_tier_limit, limiter

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
    user_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], user_id)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if file.content_type not in ["audio/wav", "audio/x-wav", "audio/mp3"]:
        raise HTTPException(status_code=400, detail="Invalid audio format. Use WAV or MP3.")

    now = datetime.utcnow()
    if user.last_gpt_reset.month != now.month or user.last_gpt_reset.year != now.year:
        user.monthly_voice_count = 0
        user.last_voice_reset = now

    monthly_limit = get_monthly_limit(user.tier)

    if user.tier == TierLevel.free:
        total_usage = user.monthly_gpt_count + user.monthly_voice_count
        if total_usage >= monthly_limit:
            db.commit()
            return {
                "reply": f"⚠️ You've used your {monthly_limit} total messages this month. Upgrade your plan to get more access.",
                "memory_enabled": user.memory_enabled,
                "important": False,
                "messages_used_this_month": total_usage,
                "messages_remaining": 0,
                "audio_url": None
            }
    else:
        if user.monthly_voice_count >= monthly_limit:
            db.commit()
            return {
                "reply": f"⚠️ You've used your {monthly_limit} voice messages for {user.tier} this month. Upgrade your plan to get more access.",
                "memory_enabled": user.memory_enabled,
                "important": False,
                "messages_used_this_month": user.monthly_voice_count,
                "messages_remaining": 0,
                "audio_url": None
            }

    filename = f"temp_{uuid.uuid4()}.wav"
    filepath = os.path.join("/data/audio", filename)
    with open(filepath, "wb") as f:
        f.write(await file.read())

    try:
        transcript = transcribe_audio(filepath)
        os.remove(filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    important_keywords = ["remember", "goal", "habit", "remind", "dream", "mission"]
    is_important = any(word in transcript.lower() for word in important_keywords)

    if user.memory_enabled:
        past_msgs = db.query(Message).filter(Message.user_id == user.id).order_by(Message.timestamp.desc()).limit(10).all()
        past_msgs.reverse()
        chat_history = "".join([
            f"{'User' if msg.sender == 'user' else ASSISTANT_NAME}: {msg.message}\n"
            for msg in past_msgs
        ])
        full_prompt = f"{chat_history}User: {transcript}\n{ASSISTANT_NAME}:"
    else:
        full_prompt = transcript

    try:
        assistant_reply = generate_ai_reply(full_prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")

    voice_gender = user.voice or "male"

    try:
        audio_output_path = synthesize_voice(assistant_reply, gender=voice_gender)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice synthesis failed: {str(e)}")

    if user.memory_enabled:
        db.add_all([
            Message(user_id=user.id, sender="user", message=transcript, important=is_important),
            Message(user_id=user.id, sender="assistant", message=assistant_reply, important=False),
        ])

    generated_audio = GeneratedAudio(
        user_id=user.id,
        filename=os.path.basename(audio_output_path),
    )
    db.add(generated_audio)

    user.monthly_voice_count += 1
    db.commit()

    return {
        "reply": assistant_reply,
        "memory_enabled": user.memory_enabled,
        "important": is_important,
        "messages_used_this_month": user.monthly_voice_count,
        "messages_remaining": monthly_limit - user.monthly_voice_count,
        "audio_url": f"/get-audio/{os.path.basename(audio_output_path)}"
    }


# ---------------------- AUDIO STREAMING ENDPOINT ----------------------
class GetAudioRequest(BaseModel):
    user_id: int
    filename: str
@router.post("/get-voice-chat-audio")
@limiter.limit(get_tier_limit)
async def get_voice_chat_audio(
    payload: GetAudioRequest,
    request: Request,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.user_id)

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
    return FileResponse(file_path, media_type=content_type)
