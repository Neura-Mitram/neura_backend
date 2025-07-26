# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import Request
from sqlalchemy.orm import Session
from app.models.user import User
from app.services.translation_service import translate, detect_language
from app.utils.audio_processor import synthesize_voice
import time

# Persistent interpreter state per user (reset every interaction cycle)
interpreter_speakers = {}  # {user_id: {'A': 'es', 'B': 'en', 'last': 'A', 'last_active': 123456.789}}

# Session timeout in seconds
INTERPRETER_SESSION_TIMEOUT = 300  # 5 minutes
# Interpreter inactivity timeout (deactivates interpreter mode)
INTERPRETER_INACTIVITY_TIMEOUT = 180  # 3 minutes

async def handle_interpreter_mode(
    request: Request,
    user: User,
    transcript: str,
    db: Session
):
    user_id = user.id
    spoken_lang = detect_language(transcript)
    user_gender = user.voice if user.voice in ["male", "female"] else "male"
    emotion = user.emotion_status or "joy"
    current_time = time.time()

    # 🧠 Init or reset if timed out
    mapping = interpreter_speakers.get(user_id)
    if not mapping or current_time - mapping.get("last_active", 0) > INTERPRETER_SESSION_TIMEOUT:
        interpreter_speakers[user_id] = {'A': spoken_lang, 'B': None, 'last': 'B', 'last_active': current_time}
    else:
        interpreter_speakers[user_id]['last_active'] = current_time

    mapping = interpreter_speakers[user_id]

    # 🧭 Determine speaker (A/B) by lang switch
    current_speaker = 'A' if spoken_lang == mapping['A'] else 'B'
    other_speaker = 'B' if current_speaker == 'A' else 'A'

    # 📌 Save speaker B's language if unknown
    if current_speaker == 'B' and mapping['B'] is None:
        mapping['B'] = spoken_lang

    # 🌍 Translate to other speaker's lang
    target_lang = mapping[other_speaker] or ("en" if spoken_lang != "en" else "hi")
    translated_text = translate(transcript, source_lang=spoken_lang, target_lang=target_lang)

    # 🗣 Construct voice line: Person A/B said...
    tag = "👤 A said:" if current_speaker == 'A' else "👤 B replied:"
    reply_text = f"{tag} {translated_text}"

    audio_url = synthesize_voice(
        text=reply_text,
        gender=user_gender,
        emotion=emotion,
        lang=target_lang
    )

    # 🔄 Save last speaker
    mapping['last'] = current_speaker

    # ⏱ Deactivate interpreter mode if inactive for too long
    if current_time - mapping.get("last_active", 0) > INTERPRETER_INACTIVITY_TIMEOUT:
        user.active_mode = None
        db.commit()

    return {
        "intent": "interpreter_mode",
        "original_text": transcript,
        "translated_text": translated_text,
        "speaker": current_speaker,
        "output_lang": target_lang,
        "audio_stream_url": audio_url
    }

