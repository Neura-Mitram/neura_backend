# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

import logging
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.user import User
from app.models.goal import Goal
from app.models.habit import Habit
from app.models.message_model import Message
from app.models.notification import NotificationLog
from app.utils.audio_processor import synthesize_voice
from app.utils.tier_logic import (
    is_voice_ping_allowed, is_pro_user, is_trait_decay_allowed, is_in_private_mode
)

from app.services.trait_drift_detector import detect_trait_drift
from app.services.translation_service import translate

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# -------------------------------
# Task Checkers
# -------------------------------

def should_nudge(user: User):
    now = datetime.utcnow()
    if not user.nudge_last_sent:
        return True

    delta_days = (now - user.nudge_last_sent).days

    if user.nudge_frequency == "low" and delta_days < 7:
        return False
    if user.nudge_frequency == "normal" and delta_days < 3:
        return False
    if user.nudge_frequency == "high" and delta_days < 1:
        return False

    return True

def get_overdue_goals(user: User, db: Session):
    return db.query(Goal).filter(
        Goal.user_id == user.id,
        Goal.status == "active",
        Goal.deadline.isnot(None),
        Goal.deadline < datetime.utcnow()
    ).all()

def get_stale_habits(user: User, db: Session):
    three_days_ago = datetime.utcnow() - timedelta(days=3)
    return db.query(Habit).filter(
        Habit.user_id == user.id,
        Habit.status == "active",
        Habit.last_completed.isnot(None),
        Habit.last_completed < three_days_ago
    ).all()

def detect_missed_habits_for_nudge(user: User, db: Session) -> bool:
    if not is_trait_decay_allowed(user):
        return False

    now = datetime.utcnow()
    missed_habits = []

    habits = db.query(Habit).filter(
        Habit.user_id == user.id,
        Habit.status == "active"
    ).all()

    for habit in habits:
        if habit.frequency == "daily":
            threshold = now - timedelta(days=1)
        elif habit.frequency == "weekly":
            threshold = now - timedelta(days=7)
        else:
            continue

        if not habit.last_completed or habit.last_completed < threshold:
            missed_habits.append(habit)

    return len(missed_habits) >= 2

# -------------------------------
# Delivery Channel Selector
# -------------------------------

def decide_delivery_channel(user: User, force_voice: bool = False) -> str:
    if force_voice:
        return "voice"
    if is_voice_ping_allowed(user) and user.voice_nudges_enabled and user.preferred_delivery_mode == "voice":
        return "voice"
    if user.push_notifications_enabled:
        return "local_notification"
    return "in_chat"

# -------------------------------
# Text Generator
# -------------------------------

def build_nudge_text(user: User, goals, habits):
    lines = []
    if goals:
        for g in goals:
            due = g.deadline.strftime('%b %d') if g.deadline else "no due date"
            lines.append(f"🎯 *{g.goal_text}* (due {due})")
    if habits:
        for h in habits:
            last = h.last_completed.strftime('%b %d') if h.last_completed else "not logged yet"
            lines.append(f"✅ *{h.habit_name}* (last done {last})")
    body = "\n".join(lines)
    return (
        f"Hi {user.name}, just checking in 👋\n\n"
        f"You have some pending items:\n\n"
        f"{body}\n\n"
        "Tap to review or say 'Mark as done' anytime!"
    )

def generate_emotion_based_nudge(user: User) -> str:
    emotion = user.emotion_status or "love"

    fallback_nudges = {
        "joy": "You seem upbeat today! Keep riding that wave 🌈",
        "sadness": "Just checking in 💙 You're not alone—I'm here.",
        "anger": "It's okay to feel off. I'm here if you want to vent.",
        "fear": "Everything’s going to be alright. You're not alone.",
        "love": "Sending good vibes your way 💖",
        "surprise": "Hope the day’s unfolding well! Let me know if I can help.",
    }

    return fallback_nudges.get(emotion, "Hi! Just checking in. Hope you're doing well.")

# -------------------------------
# Delivery Functions (All Modes)
# -------------------------------

def send_voice_nudge(user: User, text: str, db: Session, is_emotion: bool = False):
    try:
        user_lang = user.preferred_lang or "en"
        if user_lang != "en":
            text = translate(text, source_lang="en", target_lang=user_lang)

        stream_url = synthesize_voice(
            text,
            gender=user.voice if user.voice in ["male", "female"] else "male",
            lang=user_lang,
            emotion=user.emotion_status or "unknown"
        )

        notification = NotificationLog(
            user_id=user.id,
            notification_type="emotion_voice_nudge" if is_emotion else "voice_nudge",
            content=f"{text} [stream: {stream_url}]",
            delivered=False,
            timestamp=datetime.utcnow()
        )

        db.add(notification)
        logger.info("[VOICE NUDGE] %s for %s", "Emotion" if is_emotion else "Goal/Habit", user.name)

    except Exception as e:
        db.rollback()
        logger.error("⚠️ Failed to send voice nudge for %s: %s", user.name, str(e))

def store_local_notification(user: User, text: str, db: Session, is_emotion: bool = False):
    try:
        user_lang = user.preferred_lang or "en"
        if user_lang != "en":
            text = translate(text, source_lang="en", target_lang=user_lang)

        notification = NotificationLog(
            user_id=user.id,
            content=text,
            notification_type="emotion_notification" if is_emotion else "local_notification",
            delivered=False,
            timestamp=datetime.utcnow()
        )

        db.add(notification)
        logger.info("[NOTIFICATION] %s for %s", "Emotion" if is_emotion else "Goal/Habit", user.name)

    except Exception as e:
        db.rollback()
        logger.error("⚠️ Failed to store local notification for %s: %s", user.name, str(e))

def store_in_chat_prompt(user: User, text: str, db: Session, is_emotion: bool = False):
    message = Message(
        user_id=user.id,
        role="assistant",
        content=text,
        is_prompt=True,
        metadata="emotion_nudge" if is_emotion else "in_chat"
    )
    db.add(message)
    logger.info("[IN-CHAT] %s for %s", "Emotion" if is_emotion else "Goal/Habit", user.name)

# -------------------------------
# Main Scheduler
# -------------------------------

def process_nudges():
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()

        for user in users:
            if is_in_private_mode(user):
                logger.info(f"🔒 Skipped nudge for user {user.id} — Private Mode active.")
                continue
            try:
                overdue_goals = get_overdue_goals(user, db)
                overdue_habits = get_stale_habits(user, db)
                has_task = overdue_goals or overdue_habits or detect_missed_habits_for_nudge(user, db)

                drift_summary = detect_trait_drift(user, db)

                if not has_task:
                    # ✅ First check: drift-based nudge
                    if drift_summary:
                        channel = decide_delivery_channel(user)
                        if channel == "voice":
                            send_voice_nudge(user, drift_summary, db, is_emotion=True)
                        elif channel == "local_notification":
                            store_local_notification(user, drift_summary, db, is_emotion=True)
                        else:
                            store_in_chat_prompt(user, drift_summary, db, is_emotion=True)

                        user.nudge_last_sent = datetime.utcnow()
                        user.nudge_last_type = channel
                        db.commit()
                        continue

                    # ✅ Fallback: emotion nudge
                    if not is_trait_decay_allowed(user):
                        continue

                    emotion_text = generate_emotion_based_nudge(user)
                    channel = decide_delivery_channel(user)
                    if channel == "voice":
                        send_voice_nudge(user, emotion_text, db, is_emotion=True)
                    elif channel == "local_notification":
                        store_local_notification(user, emotion_text, db, is_emotion=True)
                    else:
                        store_in_chat_prompt(user, emotion_text, db, is_emotion=True)

                    user.nudge_last_sent = datetime.utcnow()
                    user.nudge_last_type = channel
                    db.commit()
                    continue

                # ✅ Skip if user was already nudged recently
                if not should_nudge(user):
                    continue

                    # ✅ Respect emotion safety filter
                if is_pro_user(user) and user.emotion_status in ["sadness", "anger", "fear"]:
                    logger.info("😔 Skipping nudge for user %s due to emotion: %s", user.id, user.emotion_status)
                    continue

                    # ✅ Nudge user with goal/habit reminder
                force_voice = (user.tier.name == "free" and (datetime.utcnow() - user.created_at).days <= 7)
                channel = decide_delivery_channel(user, force_voice=force_voice)

                logger.info("📤 Nudge type: %s | User: %s", channel, user.name)

                nudge_text = build_nudge_text(user, overdue_goals, overdue_habits)
                if channel == "voice":
                    send_voice_nudge(user, nudge_text, db)
                elif channel == "local_notification":
                    store_local_notification(user, nudge_text, db)
                else:
                    store_in_chat_prompt(user, nudge_text, db)

                user.nudge_last_sent = datetime.utcnow()
                user.nudge_last_type = channel
                db.commit()

            except Exception as e:
                db.rollback()
                logger.error("⚠️ Nudge failed for user %s: %s", user.id, str(e))

    finally:
        db.close()

# -------------------------------
# On-Demand Intent Handler
# -------------------------------

def generate_nudge_for_user(user: User, db: Session) -> str:
    overdue_goals = get_overdue_goals(user, db)
    overdue_habits = get_stale_habits(user, db)
    if not overdue_goals and not overdue_habits:
        if detect_missed_habits_for_nudge(user, db):
            return "You've missed a few habit reminders lately. Let’s restart that streak 💪"
        return generate_emotion_based_nudge(user)
    return build_nudge_text(user, overdue_goals, overdue_habits)
