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

router = APIRouter()

# ✅ Helper for decoding token inside WebSocket

def decode_token(token: str) -> dict:
    return verify_access_token(token)


# ✅ New Real-Time Voice Input Stream
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
        user_data = decode_token(token)
        user = db.query(User).filter(User.temp_uid == user_data["sub"]).first()
        if not user:
            await websocket.send_json({"error": "Invalid user"})
            return

        # ✅ Step 2: Optional headers
        battery_level = int(websocket.headers.get("x-battery-level", user.battery_level or 100))
        preferred_lang = websocket.headers.get("x-preferred-language", user.preferred_lang or "en")

        # ✅ Step 3: Silence timeout by tier
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

            # If silence or enough time passed → process buffer
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
                    monthly_limit=100  # Optional: use tier-based if needed
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
    model_id: str = "eleven_multilingual_v2"
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
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
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
