# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


import os
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.user import User, TierLevel
from app.services.trait_summary_service import generate_weekly_trait_summary
from app.utils.audio_processor import synthesize_voice
from app.models.notification import NotificationLog
from app.services.translation_service import translate

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def weekly_trait_summaries_cron():
    db: Session = SessionLocal()
    try:
        users = db.query(User).filter(
            User.tier.in_([TierLevel.basic, TierLevel.pro]),
            User.voice_nudges_enabled == True,
            User.hourly_ping_enabled == True,
            User.preferred_delivery_mode == "voice",
            getattr(User, "is_active", True) == True  # ✅ Safe fallback if field missing
        ).all()

        for user in users:
            try:
                summary_text = generate_weekly_trait_summary(user, db)
                user_lang = user.preferred_lang or "en"
                voice_gender = user.voice if user.voice in ["male", "female"] else "female"
                emotion = user.emotion_status or "unknown"

                # 🌐 Translate summary if needed
                if user_lang != "en":
                    summary_text = translate(summary_text, source_lang="en", target_lang=user_lang)

                stream_url = synthesize_voice(
                    summary_text,
                    gender=voice_gender,
                    lang=user_lang,
                    emotion=emotion
                )

                notification = NotificationLog(
                    user_id=user.id,
                    notification_type="weekly_trait_voice_summary",
                    content=f"{summary_text} [stream: {stream_url}]",
                    delivered=False,
                    timestamp=datetime.utcnow()
                )

                db.add(notification)
                logger.info(f"📢 Weekly summary voice sent for user: {user.id}")

            except Exception as e:
                logger.warning(f"⚠️ Failed summary for user {user.id}: {e}")

        db.commit()
    finally:
        db.close()