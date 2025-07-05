# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


import logging
from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.ai_engine import generate_ai_reply
from transformers import pipeline

logger = logging.getLogger(__name__)

# Initialize pipeline only once
emotion_classifier = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base"
)

async def update_emotion_status(user: User, recent_prompt: str, db: Session) -> str:
    """
    Analyzes the emotion of the user message and updates the user.emotion_status.
    Returns the detected emotion label or 'unknown'.
    """
    try:
        result = emotion_classifier(recent_prompt)[0]
        emotion_label = result["label"].lower()

        valid_emotions = ["joy", "anger", "fear", "sadness", "love", "surprise"]
        if emotion_label in valid_emotions:
            user.emotion_status = emotion_label
            db.commit()
            logger.info(f"🎭 Emotion status updated for user {user.id} → {emotion_label}")
            return emotion_label
        else:
            logger.warning(f"⚠️ Invalid emotion response: '{emotion_label}'")
            return "unknown"
    except Exception as e:
        logger.error(f"❌ Emotion update failed for user {user.id}: {e}")
        return "unknown"
