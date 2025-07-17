# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from fastapi import Request
from sqlalchemy.orm import Session
from app.models.user import User
from app.services.translation_service import translate
from app.utils.audio_processor import synthesize_voice

async def handle_interpreter_mode(
    request: Request,
    user: User,
    transcript: str,
    db: Session
):
    """
    Translates user's spoken input and returns the translated text with audio stream.
    Designed for real-time interpreter mode.
    """
    input_lang = user.preferred_lang or "en"

    # ⚙️ You can enhance this logic to detect or allow frontend override
    output_lang = "en" if input_lang != "en" else "hi"

    try:
        translated_text = translate(transcript, source_lang=input_lang, target_lang=output_lang)

        voice_gender = user.voice if user.voice in ["male", "female"] else "male"
        emotion = user.emotion_status or "unknown"

        audio_stream_url = synthesize_voice(
            text=translated_text,
            gender=voice_gender,
            lang=output_lang,
            emotion=emotion
        )

        return {
            "intent": "interpreter_mode",
            "original_text": transcript,
            "translated_text": translated_text,
            "audio_stream_url": audio_stream_url,
            "input_lang": input_lang,
            "output_lang": output_lang
        }

    except Exception as e:
        return {
            "intent": "interpreter_mode",
            "status": "error",
            "message": "Translation or TTS failed.",
            "detail": str(e)
        }

