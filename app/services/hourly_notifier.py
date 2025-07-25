# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.



import logging
import asyncio
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.user import User, TierLevel
from app.utils.voice_sender import send_voice_to_neura
from app.utils.ambient_guard import (
    is_night_time,
    is_fragile_emotion,
    is_gps_near_unsafe_area,
    should_throttle_ping
)

from app.services.nudge_service import generate_nudge_for_user
from app.services.trait_drift_detector import detect_trait_drift

from app.utils.tier_logic import is_in_private_mode
from app.services.translation_service import translate

from app.utils.location_utils import deliver_travel_tip
from app.utils.ambient_guard import is_night_time, is_fragile_emotion, is_gps_near_unsafe_area
from app.utils.firebase import send_fcm_push

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def get_time_based_prompt(user: User) -> str:
    hour = datetime.now().hour
    time_context = (
        "morning" if 5 <= hour < 12 else
        "afternoon" if 12 <= hour < 18 else
        "evening" if 18 <= hour < 22 else
        "night"
    )

    emotion = user.emotion_status or ""

    if emotion == "sadness":
        return "Just checking in 💙 You're not alone—I'm here."
    elif emotion == "tired":
        return "Hi, just checking in. Maybe it's a good moment to pause and rest."
    elif emotion == "joy":
        return "I love that you're feeling good today! Keep shining."
    elif emotion == "anger":
        return "It’s okay to feel frustrated sometimes. I’m here if you need a reset."
    elif emotion == "fear":
        return "Everything’s going to be alright. You’ve got this. 🫶"
    elif emotion == "surprise":
        return "Sounds like an unexpected day! I’m here if you want to talk."
    elif emotion == "love":
        return "Sending warmth and good vibes your way 💖"

    # Fallback to time-based prompts
    prompts = {
        "morning": [
            "Good morning! Ready to make today amazing?",
            "Hi there, hope you woke up refreshed.",
            "Morning! I'm here if you want to plan your day."
        ],
        "afternoon": [
            "Hey, how's your day going so far?",
            "I'm here if you need a break.",
            "Hi! Just checking in to see how you're feeling."
        ],
        "evening": [
            "Good evening. Want to unwind together?",
            "Hope your day went well. Anything on your mind?",
            "Evening check-in—I'm here to help if you need me."
        ],
        "night": [
            "It's late—remember to rest well.",
            "Hi, just making sure you're okay before bed.",
            "Time to relax. Sweet dreams when you're ready!"
        ]
    }

    return random.choice(prompts[time_context])

async def run_hourly_notifier():
    db: Session = SessionLocal()
    try:
        users = db.query(User).filter(
            User.tier.in_([TierLevel.basic, TierLevel.pro]),
            User.hourly_ping_enabled == True,
            User.preferred_delivery_mode == "voice",
            User.voice_nudges_enabled == True
        ).all()

        tasks = []
        now = datetime.utcnow()

        for user in users:

            if is_in_private_mode(user):
                logger.info(f"🔒 Skipped user {user.id} — Private Mode active.")
                continue

            if is_night_time(user):
                logger.info(f"🌙 Skipped user {user.id} due to night-time.")
                continue

            if is_fragile_emotion(user):
                logger.info(f"😔 Skipped user {user.id} due to fragile emotional state.")
                continue

            if is_gps_near_unsafe_area(user, db):
                logger.info(f"📍 Skipped user {user.id} due to proximity to unsafe zone.")
                continue

            if should_throttle_ping(user):
                logger.info(f"⏱️ Skipped user {user.id} due to recent nudge.")
                continue

            # ✅ Inject travel tip before regular nudges
            await maybe_send_travel_tip(user, db)

            # 🧠 Try smart nudge first
            try:
                nudge_text = generate_nudge_for_user(user, db)
                if nudge_text.strip() == "":
                    raise Exception("Empty nudge")
            except Exception:
                # Try drift nudge fallback
                nudge_text = detect_trait_drift(user, db)

            if not nudge_text:
                # Final fallback two types
                if user.last_travel_tip_sent and (datetime.utcnow() - user.last_travel_tip_sent).days < 1:
                    nudge_text = get_generic_travel_fallback()
                else:
                    nudge_text = get_time_based_prompt(user)

                # 🌐 Translate if user prefers a native language
                user_lang = user.preferred_lang or "en"
                if user_lang != "en":
                    try:
                        nudge_text = translate(nudge_text, source_lang="en", target_lang=user_lang)
                    except Exception as e:
                        logger.warning(f"⚠️ Translation failed for user {user.id}: {e}")

                logger.info(f"🔔 Sending hourly nudge to {user.id} ({user.temp_uid})")

                tasks.append(send_voice_to_neura(
                    text=nudge_text,
                    device_id=user.temp_uid,
                    gender=user.voice,
                    request=None,
                    emotion=user.emotion_status or "unknown",
                    lang=user_lang
                ))

                # ✅ Also push FCM fallback for Kotlin overlay
                if user.fcm_token:
                    try:
                        send_fcm_push(
                            token=user.fcm_token,
                            data={
                                "hourly_text": nudge_text,
                                "hourly_lang": user_lang,
                                "hourly_emoji": "⏰"
                            }
                        )
                        logger.info(f"📲 Sent hourly FCM fallback to {user.id}")
                    except Exception as e:
                        logger.warning(f"⚠️ FCM hourly push failed for user {user.id}: {e}")

            user.last_hourly_nudge_sent = now

        db.commit()
        await asyncio.gather(*tasks)

    finally:
        db.close()

async def maybe_send_travel_tip(user: User, db: Session) -> bool:

    if is_night_time(user) or is_fragile_emotion(user) or is_gps_near_unsafe_area(user, db):
        return False

    # Optional throttle (daily)
    if user.last_travel_tip_sent and (datetime.utcnow() - user.last_travel_tip_sent).days < 1:
        return False

    try:
        await deliver_travel_tip(user, db, user.last_lat, user.last_lon)
        return True
    except Exception as e:
        logger.error(f"⚠️ Failed to send travel tip for {user.id}: {e}")
        return False

def get_generic_travel_fallback() -> str:
    prompts = [
        "Hi! Just checking in 👋 Hope you're settling in well.",
        "Neura here — if you're exploring somewhere new, I'm with you!",
        "Hope your journey is going smoothly 🛫 Let me know if you need tips.",
        "Settling in okay? I'm just a wakeword away 😊",
        "If you're in a new place, don’t forget to stay safe and hydrated 💧",
        "Hey traveler 👣 Let me know if you'd like local suggestions.",
        "Hope you're enjoying your day. Want a quick vibe check?"
    ]
    return random.choice(prompts)

def hourly_notify_users():
    asyncio.run(run_hourly_notifier())