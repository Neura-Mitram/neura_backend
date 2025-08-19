# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

import os
from dotenv import load_dotenv
from faster_whisper import WhisperModel
import aiohttp
import tempfile
import uuid
from storage3 import create_client

load_dotenv()  # Load environment variables from .env

# ------------------- Whisper Transcription -------------------

# Load Whisper model (small footprint)
whisper_model = WhisperModel("tiny", compute_type="int8")

def transcribe_audio(filepath: str) -> str:
    """
    Transcribes speech from the given audio file using Whisper.
    Returns the full transcription string.
    """
    try:
        segments, _ = whisper_model.transcribe(filepath)
        transcript = " ".join(segment.text for segment in segments)
        return transcript.strip()
    except Exception as e:
        return f"[Transcription Error: {e}]"

def transcribe_audio_bytes(file_bytes: bytes) -> str:
    """
    Transcribes audio from in-memory bytes using Whisper.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        tmp.write(file_bytes)
        tmp.flush()
        return transcribe_audio(tmp.name)

# ------------------- Text-to-Speech with ElevenLabs -------------------

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY not set in environment variables.")

ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"

# Supabase Storage
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = "neura_tts_audio"

# ------------------- Voice / Emotion Settings -------------------

EMOTION_VOICE_SETTINGS = {
    "joy": {"stability": 0.3, "similarity_boost": 0.85},
    "anger": {"stability": 0.2, "similarity_boost": 0.7},
    "fear": {"stability": 0.6, "similarity_boost": 0.6},
    "sadness": {"stability": 0.7, "similarity_boost": 0.5},
    "love": {"stability": 0.4, "similarity_boost": 0.8},
    "surprise": {"stability": 0.3, "similarity_boost": 0.9},
    "unknown": {"stability": 0.5, "similarity_boost": 0.75},
}

# Fallback voice IDs
DEFAULT_VOICE_MAP = {
    "female": "onwK4e9ZLuTAKqWW03F9",  # Grace
    "male": "EXAVITQu4vr4xnSDxMaL"     # Antoni
}

# Multilingual voice selection
LANG_VOICE_MAP = {
    lang_code: {
        "female": DEFAULT_VOICE_MAP["female"],
        "male": DEFAULT_VOICE_MAP["male"]
    } for lang_code in [
        "ar", "bg", "zh", "hr", "cs", "da", "nl", "en", "fil", "fi", "fr", "de",
        "el", "hi", "id", "it", "ja", "ko", "ms", "pl", "pt", "ro", "ru", "sk",
        "es", "sv", "ta", "tr", "uk", "hu", "no", "vi"
    ]
}

# ------------------- Async Supabase Client -------------------

storage = create_client(
    url=SUPABASE_URL,
    headers={"apiKey": SUPABASE_KEY},
    is_async=True
)

# ------------------- Async Text-to-Speech -------------------

async def synthesize_voice(
    text: str,
    gender: str = "male",
    emotion: str = "unknown",
    lang: str = "en"
) -> str:
    """
    - Calls ElevenLabs API for speech synthesis
    - Uploads audio to Supabase Storage asynchronously
    - Returns a signed public URL to the audio
    """
    # -------- Voice Selection --------
    voice_opts = LANG_VOICE_MAP.get(lang, DEFAULT_VOICE_MAP)
    voice_id = voice_opts.get(gender, DEFAULT_VOICE_MAP.get(gender, DEFAULT_VOICE_MAP["male"]))
    settings = EMOTION_VOICE_SETTINGS.get(emotion, EMOTION_VOICE_SETTINGS["unknown"])

    # -------- ElevenLabs API Request --------
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "voice_settings": {
            "stability": settings["stability"],
            "similarity_boost": settings["similarity_boost"]
        },
        "generation_config": {"language": lang}
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"},
            json=payload
        ) as resp:
            if resp.status != 200:
                raise Exception(f"TTS error: {resp.status} {await resp.text()}")
            audio_bytes = await resp.read()

    # -------- Generate filename --------
    filename = f"{uuid.uuid4()}.mp3"

    # -------- Async upload to Supabase --------
    upload_response = await storage.from_(SUPABASE_BUCKET).upload(filename, audio_bytes)
    if "error" in upload_response and upload_response["error"]:
        raise Exception(f"Supabase upload failed: {upload_response['error']}")

    # -------- Async generate signed URL (1 hour) --------
    signed_url_response = await storage.from_(SUPABASE_BUCKET).create_signed_url(filename, 3600)
    signed_url = signed_url_response.get("signedURL") or signed_url_response.get("signed_url")
    if not signed_url:
        raise Exception(f"Signed URL generation failed: {signed_url_response}")

    # Ensure full URL
    if not signed_url.startswith("http"):
        signed_url = f"{SUPABASE_URL}{signed_url}"

    return signed_url
