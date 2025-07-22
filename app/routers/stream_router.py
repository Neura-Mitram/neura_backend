# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import aiohttp
import os
import json
import tempfile
import time
from app.utils.audio_processor import transcribe_audio
from app.models.database import SessionLocal
from app.models.user import User, TierLevel
from app.utils.jwt_utils import verify_access_token
from app.routers.voice_router import process_voice_input
from app.utils.tier_logic import get_monthly_limit
from app.utils.audio_processor import synthesize_voice
from app.services.translation_service import translate

router = APIRouter()

# ✅ Helper for decoding token inside WebSocket

def decode_token(token: str) -> dict:
    return verify_access_token(token)


@router.websocket("/ws/audio-stream")
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
                "important": True
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
            TierLevel.basic: 1.2,
            TierLevel.pro: 0.9
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


