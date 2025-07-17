# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

import os
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from urllib.parse import urlencode

# ------------------- Whisper Transcription -------------------

# Load Whisper model (small footprint for Hugging Face Spaces)
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

# ------------------- Text-to-Speech with ElevenLabs (Streaming) -------------------

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY") #sk_cc5a28fc410d5becc5b4c127c8a02830ae22d230ac57ffcc
ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"

# Emotion → voice settings
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

def synthesize_voice(text: str, gender: str = "male", emotion: str = "unknown", lang: str = "en") -> str:
    """
    Returns a streamable ElevenLabs WebSocket URL for the given text.
    This does NOT save audio to disk.
    Supports language fallback.
    """
    voice_opts = LANG_VOICE_MAP.get(lang, DEFAULT_VOICE_MAP)
    voice_id = voice_opts.get(gender, DEFAULT_VOICE_MAP.get(gender, DEFAULT_VOICE_MAP["male"]))

    settings = EMOTION_VOICE_SETTINGS.get(emotion, EMOTION_VOICE_SETTINGS["unknown"])

    query = urlencode({
        "text": text,
        "voice_id": voice_id,
        "model_id": ELEVENLABS_MODEL_ID,
        "stability": settings["stability"],
        "similarity_boost": settings["similarity_boost"]
    })

    return f"wss://byshiladityamallick-neura-smart-assistant.hf.space/stream/elevenlabs?{query}"

def transcribe_audio_bytes(file_bytes: bytes) -> str:
    """
    Transcribes audio from in-memory bytes using Whisper.
    """
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        tmp.write(file_bytes)
        tmp.flush()
        return transcribe_audio(tmp.name)
