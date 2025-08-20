# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


import os
import logging
import requests
from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.trait_logger import log_user_trait

logger = logging.getLogger(__name__)

# ✅ Hugging Face Inference API Setup
if os.getenv("ENV") != "production":
    from dotenv import load_dotenv
    load_dotenv()

HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
EMOTION_MODEL_ID = "j-hartmann/emotion-english-distilroberta-base"

API_URL = f"https://api-inference.huggingface.co/models/{EMOTION_MODEL_ID}"
HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

def _call_emotion_api(text: str) -> str:
    try:
        response = requests.post(API_URL, headers=HEADERS, json={"inputs": text})
        response.raise_for_status()
        result = response.json()

        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
            predictions = result[0]
            top = max(predictions, key=lambda x: x.get("score", 0))
            label = top["label"].lower()
            valid = ["joy", "anger", "fear", "sadness", "love", "surprise"]
            return label if label in valid else "unknown"
        else:
            logger.warning(f"⚠️ Unexpected emotion API response format: {result}")
            return "unknown"
    except Exception as e:
        logger.warning(f"❌ Emotion API call failed: {e}")
        return "unknown"


async def update_emotion_status(user: User, recent_prompt: str, db: Session, source: str = "chat_or_voice") -> str:
    """
    Analyzes user emotion and updates `user.emotion_status` in DB.
    Logs trait for memory tracking.
    """
    emotion_label = _call_emotion_api(recent_prompt)

    if emotion_label != "unknown":
        try:
            user.emotion_status = emotion_label
            db.commit()
            log_user_trait(db, user, "emotion", emotion_label, source)
            logger.info(f"🎭 Emotion updated for user {user.id} → {emotion_label}")
        except Exception as e:
            logger.warning(f"⚠️ Emotion DB update failed: {e}")

    return emotion_label


def infer_emotion_label(text: str) -> str:
    """Returns the emotion label from Hugging Face model for individual message storage."""
    return _call_emotion_api(text)
