# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


import logging
from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.ai_engine import generate_ai_reply
from transformers import pipeline
from app.utils.trait_logger import log_user_trait

logger = logging.getLogger(__name__)

# Initialize pipeline only once
emotion_classifier = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base"
)

async def update_emotion_status(user: User, recent_prompt: str, db: Session, source: str = "chat_or_voice") -> str:
    """
    Analyzes the emotion of the user message and updates the user.emotion_status.
    Returns the detected emotion label or 'unknown'.
    Also logs the trait for memory graph tracking.
    """
    try:
        result = emotion_classifier(recent_prompt)[0]
        emotion_label = result["label"].lower()

        valid_emotions = ["joy", "anger", "fear", "sadness", "love", "surprise"]
        if emotion_label in valid_emotions:
            user.emotion_status = emotion_label
            db.commit()
            logger.info(f"🎭 Emotion status updated for user {user.id} → {emotion_label}")

            # ✅ Log emotion as trait
            log_user_trait(db, user, trait_type="emotion", trait_value=emotion_label, source=source)

            return emotion_label
        else:
            logger.warning(f"⚠️ Invalid emotion response: '{emotion_label}'")
            return "unknown"
    except Exception as e:
        logger.error(f"❌ Emotion update failed for user {user.id}: {e}")
        return "unknown"


def infer_emotion_label(text: str) -> str:
    """
    Returns the emotion label from HuggingFace model for individual message storage.
    """
    try:
        result = emotion_classifier(text)[0]
        label = result["label"].lower()
        valid_emotions = ["joy", "anger", "fear", "sadness", "love", "surprise"]
        return label if label in valid_emotions else "unknown"
    except Exception as e:
        logger.warning(f"Emotion inference failed for message: {e}")
        return "unknown"
