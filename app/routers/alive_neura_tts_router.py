# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


import os
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.utils.auth_utils import require_token
from app.schemas.tts_schemas import GenerateTTSRequest
from app.utils.audio_processor import synthesize_voice
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/generate-tts-audio-once")
def generate_tts_audio_once(
    request: Request,
    payload: GenerateTTSRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    try:
        # ✅ Verify user ownership
        if str(user_data["sub"]) != str(payload.device_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized"
            )

        # ✅ Generate TTS audio file
        file_path = synthesize_voice(
            payload.text,
            gender=payload.voice,
            output_folder="/data/audio/temp_audio"
        )

        # ✅ Make sure file exists
        if not os.path.isfile(file_path):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="TTS synthesis failed: output file not found."
            )

        # ✅ Build public URL
        public_url = str(request.base_url) + f"audio/temp_audio/{os.path.basename(file_path)}"

        # ✅ Return the URL
        return {"audio_url": public_url}

    except HTTPException:
        # Let any HTTPException propagate cleanly
        raise

    except Exception as e:
        # ✅ Log the full stack trace in server logs
        logger.exception("Unexpected error generating TTS audio")

        # ✅ Return a consistent 500 error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )



