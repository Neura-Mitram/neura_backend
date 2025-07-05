# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.utils.auth_utils import require_token
from app.schemas.tts import GenerateTTSRequest
from app.utils.voice_utils import synthesize_voice
from app.utils.rate_limit_utils import get_tier_limit, limiter

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/generate-tts-audio-once")
@limiter.limit(get_tier_limit)
def generate_tts_audio_once(
    payload: GenerateTTSRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    # ✅ Verify user ownership
    if str(user_data["sub"]) != str(payload.user_id):
        raise HTTPException(status_code=403, detail="Unauthorized")

    # ✅ Generate TTS audio file
    file_path = synthesize_voice(payload.text, payload.voice)

    # ✅ Read file content
    try:
        with open(file_path, "rb") as f:
            data = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read audio: {e}")

    # ✅ Delete the file immediately
    try:
        os.remove(file_path)
    except Exception as e:
        # Not fatal, just log
        print(f"[WARN] Could not delete audio file: {e}")

    # ✅ Stream back to client
    return StreamingResponse(
        iter([data]),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": 'inline; filename="speech.mp3"',
            "Content-Length": str(len(data))
        }
    )



