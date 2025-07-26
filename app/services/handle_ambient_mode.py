# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.



from datetime import datetime
from app.models.notification import NotificationLog
from app.utils.audio_processor import synthesize_voice
from app.services.translation_service import translate
from app.services.emotion_tone_updater import update_emotion_status
from app.utils.red_flag_utils import detect_red_flag, SEVERE_KEYWORDS
from app.services.trait_drift_detector import detect_trait_drift


async def handle_ambient_mode(user, transcript: str, db):
    # Step 1: Emotion analysis (also logs to trait logs)
    emotion_label = await update_emotion_status(user, transcript, db, source="ambient_passive")

    # Step 2: Use existing trait drift detector
    drift_message = detect_trait_drift(user, db)

    # Step 3: If drift is found, push a nudge (voice or text based on context)
    if drift_message and user.voice_nudges_enabled:
        user_lang = user.preferred_lang or "en"
        nudge_text = translate(drift_message, source_lang="en", target_lang=user_lang) if user_lang != "en" else drift_message

        low_battery = user.battery_level is not None and user.battery_level < 15
        no_speaker = user.output_audio_mode != "speaker"

        if low_battery or no_speaker:
            db.add(NotificationLog(
                user_id=user.id,
                notification_type="ambient_drift_text",
                content=nudge_text,
                delivered=False,
                timestamp=datetime.utcnow()
            ))
        else:
            stream_url = synthesize_voice(
                text=nudge_text,
                gender=user.voice or "female",
                emotion=emotion_label,
                lang=user_lang
            )
            db.add(NotificationLog(
                user_id=user.id,
                notification_type="ambient_drift_voice",
                content=f"{nudge_text} [stream: {stream_url}]",
                delivered=False,
                timestamp=datetime.utcnow()
            ))

        db.commit()

    # Step 4: SOS detection
    if detect_red_flag(transcript) == "sos":
        is_force = any(term in transcript.lower() for term in SEVERE_KEYWORDS)
        return {
            "reply": "🚨 Emergency detected in ambient mode.",
            "trigger_sos": True,
            "trigger_sos_force": is_force,
            "audio_stream_url": None
        }

    # Step 5: Silent response — ambient log only
    return {
        "status": "ambient_log_success",
        "emotion": emotion_label,
        "drift_detected": bool(drift_message),
        "drift_message": drift_message,
        "audio_stream_url": None
    }
