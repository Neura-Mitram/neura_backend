# hourly_notifier.py

import logging
import asyncio
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User, TierLevel
from app.utils.ai_engine import generate_ai_reply
import random
from datetime import datetime
from app.utils.voice_sender import send_voice_to_neura

# Configure logger if not already done elsewhere
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_prompt(user):
    now = datetime.now()
    hour = now.hour

    # Determine time of day
    if 5 <= hour < 12:
        time_context = "morning"
    elif 12 <= hour < 18:
        time_context = "afternoon"
    elif 18 <= hour < 22:
        time_context = "evening"
    else:
        time_context = "night"

    # Mood-specific messages
    if user.emotion_status == "stressed":
        return "I sense things might feel a bit heavy right now. Remember, I'm always here for you."
    elif user.emotion_status == "tired":
        return "Hi, just checking in. Maybe it's a good moment to pause and rest."
    elif user.emotion_status == "happy":
        return "I love that you're feeling good today! Keep shining."

    # Time-based friendly prompts
    morning_prompts = [
        "Good morning! Ready to make today amazing?",
        "Hi there, hope you woke up refreshed.",
        "Morning! I'm here if you want to plan your day."
    ]

    afternoon_prompts = [
        "Hey, how's your day going so far?",
        "I'm here if you need a break.",
        "Hi! Just checking in to see how you're feeling."
    ]

    evening_prompts = [
        "Good evening. Want to unwind together?",
        "Hope your day went well. Anything on your mind?",
        "Evening check-in—I'm here to help if you need me."
    ]

    night_prompts = [
        "It's late—remember to rest well.",
        "Hi, just making sure you're okay before bed.",
        "Time to relax. Sweet dreams when you're ready!"
    ]

    if time_context == "morning":
        prompt = random.choice(morning_prompts)
    elif time_context == "afternoon":
        prompt = random.choice(afternoon_prompts)
    elif time_context == "evening":
        prompt = random.choice(evening_prompts)
    else:
        prompt = random.choice(night_prompts)

    return prompt


async def run_hourly_notifier():
    db: Session = SessionLocal()

    try:
        users = db.query(User).filter(
            User.tier.in_([TierLevel.basic, TierLevel.pro]),
            User.hourly_ping_enabled == True,
            User.preferred_delivery_mode == "voice"
        ).all()

        tasks = []
        for user in users:
            prompt = get_prompt(user)
            tasks.append(send_voice_to_neura(user.id, prompt))

        await asyncio.gather(*tasks)

    finally:
        db.close()


def hourly_notify_users():
    asyncio.run(run_hourly_notifier())
