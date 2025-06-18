from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from utils.audio_processor import transcribe_audio, synthesize_voice
from utils.ai_engine import generate_ai_reply
from utils.tier_check import get_monthly_limit
from models.message_model import Message
from models.database import SessionLocal
from models.user_model import User
from datetime import datetime
import os
import uuid
import mimetypes

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/voice-chat")
async def voice_chat(
    user_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # ✅ Validate user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 🎙️ Validate audio format
    if file.content_type not in ["audio/wav", "audio/x-wav", "audio/mp3"]:
        raise HTTPException(status_code=400, detail="Invalid audio format. Use WAV or MP3.")

    # 🔁 Auto-reset voice usage if month changed
    now = datetime.utcnow()
    if user.last_gpt_reset.month != now.month or user.last_gpt_reset.year != now.year:
        user.monthly_voice_count = 0
        user.last_voice_reset = now

    # 🔒 Check monthly tier limit
    monthly_limit = get_monthly_limit(user.tier)
    if user.monthly_gpt_count >= monthly_limit:
        db.commit()
        return {
            "reply": f"⚠️ You've used your {monthly_limit} voice chats for {user.tier} this month.",
            "memory_enabled": user.memory_enabled,
            "important": False,
            "messages_used_this_month": user.monthly_voice_count,
            "messages_remaining": 0,
            "audio_url": None
        }

    # 💾 Save and transcribe uploaded audio
    filename = f"temp_{uuid.uuid4()}.wav"
    filepath = os.path.join("audio", filename)  # <- Save to audio/ folder
    with open(filepath, "wb") as f:
        f.write(await file.read())

    transcript = transcribe_audio(filepath)
    os.remove(filepath)  # Optional cleanup

    # ✨ Keyword detection
    important_keywords = ["remember", "goal", "habit", "remind", "dream", "mission"]
    is_important = any(word in transcript.lower() for word in important_keywords)

    # 🧠 Use memory context
    chat_history = ""
    if user.memory_enabled:
        past_msgs = db.query(Message) \
            .filter(Message.user_id == user.id) \
            .order_by(Message.timestamp.desc()) \
            .limit(10).all()
        past_msgs.reverse()

        for msg in past_msgs:
            role = "User" if msg.sender == "user" else "Aditya"
            chat_history += f"{role}: {msg.message}\n"
        full_prompt = f"{chat_history}User: {transcript}\nAditya:"
    else:
        full_prompt = transcript

    # 🤖 AI reply
    assistant_reply = generate_ai_reply(full_prompt)

    # 🔉 Synthesize reply to voice
    voice_gender = user.voice or "male"
    audio_output_path = synthesize_voice(assistant_reply, gender=voice_gender)

    # 🧠 Save conversation if memory enabled
    if user.memory_enabled:
        db.add_all([
            Message(user_id=user.id, sender="user", message=transcript, important=is_important),
            Message(user_id=user.id, sender="assistant", message=assistant_reply, important=False),
        ])

    # ✅ Update usage
    user.monthly_gpt_count += 1
    db.commit()

    return {
        "reply": assistant_reply,
        "memory_enabled": user.memory_enabled,
        "important": is_important,
        "messages_used_this_month": user.monthly_voice_count,
        "messages_remaining": monthly_limit - user.monthly_voice_count,
        "audio_url": f"/get-audio/{os.path.basename(audio_output_path)}"
    }


@router.get("/get-audio/{filename}")
async def get_audio(filename: str, request: Request):
    file_path = os.path.join("audio", filename)  # Ensure audio files are saved here

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

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
    else:
        return FileResponse(file_path, media_type=content_type)
