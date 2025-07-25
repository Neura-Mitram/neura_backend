# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


import aiohttp
import os
import json
import tempfile
import time
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.utils.jwt_utils import verify_access_token
from app.models.database import SessionLocal
from app.models.user import User, TierLevel
from app.models.message_model import Message
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
from app.services.translation_service import translate, detect_language
from app.services.handle_interpreter_mode import handle_interpreter_mode
from app.services.handle_ambient_mode import handle_ambient_mode

router = APIRouter(prefix="/ws", tags=["WebSocket Auth"])
ASSISTANT_NAME = "Neura"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Helper for decoding token inside WebSocket
def decode_token(token: str) -> dict:
    return verify_access_token(token)


@router.websocket("/audio-stream")
async def stream_audio_input(websocket: WebSocket):
    await websocket.accept()
    db = SessionLocal()
    temp_file = tempfile.NamedTemporaryFile(delete=True, suffix=".wav")

    try:
        # ✅ Step 1: Authenticate
        token = websocket.headers.get("authorization", "").replace("Bearer ", "")
        if not token:
            await websocket.send_json({"error": "Missing auth token"})
            return

        # ✅ Step 2: Token Validate
        user_data = decode_token(token)
        if not user_data:
            await websocket.send_json({"error": "Invalid auth token"})
            return

        # ✅ Step 3: Device ID Validate
        device_id = websocket.headers.get("x-device-id", "").strip()
        user = db.query(User).filter(User.temp_uid == device_id).first()
        if not user:
            await websocket.send_json({"error": "Invalid user"})
            return

        user_lang = user.preferred_lang or "en"
        user_gender = user.voice or "male"
        monthly_limit = get_monthly_limit(user.tier)
        total_usage = user.monthly_gpt_count + user.monthly_voice_count

        # ✅ Rate limit check
        def send_limit_warning(reply_text):
            audio_url = synthesize_voice(
                text=reply_text,
                gender=user_gender,
                emotion="sad",
                lang=user_lang
            )
            return {
                "reply": reply_text,
                "audio_stream_url": audio_url,
                "emotion": "sad",
                "memory_enabled": user.memory_enabled,
                "messages_used_this_month": user.monthly_voice_count,
                "messages_remaining": 0,
                "important": True,
                "voice_limit_reached": True
            }

        if user.tier == TierLevel.free and total_usage >= monthly_limit:
            reply_en = f"⚠️ You've used your {monthly_limit} total messages this month."
            reply = translate(reply_en, source_lang="en", target_lang=user_lang) if user_lang != "en" else reply_en
            await websocket.send_json(send_limit_warning(reply))
            return

        if user.tier != TierLevel.free and user.monthly_voice_count >= monthly_limit:
            reply_en = f"⚠️ You've used your {monthly_limit} voice messages this month."
            reply = translate(reply_en, source_lang="en", target_lang=user_lang) if user_lang != "en" else reply_en
            await websocket.send_json(send_limit_warning(reply))
            return

        # ✅ Tier-based silence timeout
        tier_timeout_map = {
            TierLevel.free: 1.5,
            TierLevel.basic: 1,
            TierLevel.pro: 0.0
        }
        silence_timeout = tier_timeout_map.get(user.tier, 1.2)

        buffer = b""
        last_recv = time.time()

        while True:
            chunk = await websocket.receive_bytes()
            buffer += chunk
            now = time.time()

            if now - last_recv > silence_timeout and len(buffer) > 8000:
                temp_file.seek(0)
                temp_file.write(buffer)
                temp_file.flush()

                transcript = transcribe_audio(temp_file.name)

                response = await process_voice_input(
                    transcript=transcript,
                    user=user,
                    db=db,
                    request=None,
                    conversation_id=1,
                    monthly_limit=monthly_limit
                )

                await websocket.send_json(response)
                buffer = b""

            last_recv = now

    except WebSocketDisconnect:
        print("🔌 WebSocket disconnected")
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        db.close()
        temp_file.close()
        await websocket.close()


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


# ✅ Existing TTS streaming route
@router.websocket("/stream/elevenlabs")
async def stream_elevenlabs_audio(
    websocket: WebSocket,
    text: str,
    voice_id: str,
    model_id: str = "eleven_multilingual_v2",
    lang: str = "en"  # 👈 default to English
):
    await websocket.accept()
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    if not ELEVENLABS_API_KEY:
        await websocket.send_text("Missing ElevenLabs API key.")
        await websocket.close()
        return

    try:
        url = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id={model_id}"
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(url, headers={"xi-api-key": ELEVENLABS_API_KEY}) as eleven_ws:
                await eleven_ws.send_str(json.dumps({
                    "text": text,
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                    "generation_config": {
                        "language": lang  # 👈 set language here
                    }
                }))
                async for msg in eleven_ws:
                    if msg.type == aiohttp.WSMsgType.BINARY:
                        await websocket.send_bytes(msg.data)
                    elif msg.type == aiohttp.WSMsgType.CLOSE:
                        break
    except Exception as e:
        await websocket.send_text(f"❌ Streaming error: {str(e)}")
    finally:
        await websocket.close()



async def process_voice_input(
    transcript: str,
    user: User,
    db: Session,
    request: Request = None,
    conversation_id: int = 1,
    monthly_limit: int = 100
) -> dict:

    user_lang = user.preferred_lang or "en"
    spoken_lang = detect_language(transcript)

    # 🔄 Automatically handle spoken-lang mismatch with polite response in preferred_lang
    if user.active_mode != "interpreter" and spoken_lang != user_lang:
        transcript = translate(transcript, source_lang=spoken_lang, target_lang="en")

    # ✅ Ambient drift/SOS always on
    await handle_ambient_mode(user, transcript, db)

    # ✅ Interpreter mode
    if user.active_mode == "interpreter":
        return await handle_interpreter_mode(request, user, transcript, db)

    # ✅ Speaker toggle
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

    # ✅ Interpreter toggle commands
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

    # ✅ Emotion, intent, red flag detection
    is_important = any(word in transcript.lower() for word in ["goal", "habit", "remind", "dream", "mission"])
    emotion_label = await update_emotion_status(user, transcript, db, source="voice_chat")
    await run_persona_engine(db, user)

    red_flag = detect_red_flag(transcript)

    if red_flag == "code":
        reply_text = red_flag_response(reason="code or internal details", lang=user_lang)
        return {
            "reply": reply_text,
            "memory_enabled": user.memory_enabled,
            "messages_used_this_month": user.monthly_voice_count,
            "messages_remaining": monthly_limit - user.monthly_voice_count,
            "audio_stream_url": synthesize_voice(reply_text, gender=user.voice or "female", emotion="unknown", lang=user_lang)
        }

    if red_flag == "creator":
        reply_text = creator_info_response(lang=user_lang)
        return {
            "reply": reply_text,
            "memory_enabled": user.memory_enabled,
            "messages_used_this_month": user.monthly_voice_count,
            "messages_remaining": monthly_limit - user.monthly_voice_count,
            "audio_stream_url": synthesize_voice(reply_text, gender=user.voice or "female", emotion="surprise", lang=user_lang)
        }

    if red_flag == "self_query":
        reply_text = self_query_response(ai_name=user.ai_name or "Neura", lang=user_lang)
        return {
            "reply": reply_text,
            "memory_enabled": user.memory_enabled,
            "messages_used_this_month": user.monthly_voice_count,
            "messages_remaining": monthly_limit - user.monthly_voice_count,
            "audio_stream_url": synthesize_voice(reply_text, gender=user.voice or "female", emotion="joy", lang=user_lang)
        }

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
            "audio_stream_url": synthesize_voice(reply_text, gender=user.voice or "female", emotion="fear", lang=user_lang)
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
        prompt = f"User: {transcript}\n{ASSISTANT_NAME}:"

        assistant_reply = generate_ai_reply(inject_persona_into_prompt(user, prompt, db))

        if user_lang != "en":
            assistant_reply = translate(assistant_reply, source_lang="en", target_lang=user_lang)

        audio_stream_url = synthesize_voice(
            text=assistant_reply,
            gender=user.voice or "male",
            emotion=emotion_label,
            lang=user_lang
        )

        # 🔄 Track voice usage only
        user.monthly_voice_count += 1
        db.commit()

        return {
            "reply": assistant_reply,
            "emotion": emotion_label,
            "memory_enabled": user.memory_enabled,  # still returned for UI display
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

