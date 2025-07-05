# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.user import User
from app.models.goal import Goal
from app.models.habit import Habit
from app.models.message_model import Message
from app.models.notification import NotificationLog
from app.utils.audio_processor import synthesize_voice
from app.utils.tier_logic import is_voice_ping_allowed
import os

# -------------------------------
# Cron Job or Scheduler Logic
# -------------------------------

def should_nudge(user: User):
    """
    Decide if we should nudge this user based on frequency and last sent timestamp.
    """
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
    """
    Return active goals past their deadline.
    """
    return db.query(Goal).filter(
        Goal.user_id == user.id,
        Goal.status == "active",
        Goal.deadline.isnot(None),
        Goal.deadline < datetime.utcnow()
    ).all()

def get_stale_habits(user: User, db: Session):
    """
    Return habits not marked completed in the last 3 days.
    """
    three_days_ago = datetime.utcnow() - timedelta(days=3)
    return db.query(Habit).filter(
        Habit.user_id == user.id,
        Habit.status == "active",
        Habit.last_completed.isnot(None),
        Habit.last_completed < three_days_ago
    ).all()

def decide_delivery_channel(user: User) -> str:
    """
    Determines which channel to use for the nudge.
    """
    if is_voice_ping_allowed(user) and user.voice_nudges_enabled and user.preferred_delivery_mode == "voice":
        return "voice"
    if user.push_notifications_enabled:
        return "local_notification"
    return "in_chat"

def process_nudges():
    """
    Main scheduler loop to process nudges for all active users.
    """
    db = SessionLocal()
    users = db.query(User).filter(User.is_active == True).all()

    for user in users:
        overdue_goals = get_overdue_goals(user, db)
        overdue_habits = get_stale_habits(user, db)

        if not overdue_goals and not overdue_habits:
            continue

        if not should_nudge(user):
            continue

        channel = decide_delivery_channel(user)

        if channel == "voice":
            send_voice_nudge(user, overdue_goals, overdue_habits)
        elif channel == "local_notification":
            store_local_notification(user, overdue_goals, overdue_habits)
        else:
            store_in_chat_prompt(user, overdue_goals, overdue_habits)

        user.nudge_last_sent = datetime.utcnow()
        user.nudge_last_type = channel
        db.commit()


# -------------------------------
# Nudge Type Delivery Functions
# -------------------------------

def send_voice_nudge(user, goals, habits):
    """
    Builds voice nudge text, synthesizes audio using AWS Polly,
    and stores a NotificationLog record.
    """
    text = build_nudge_text(user, goals, habits)

    audio_path = synthesize_voice(
        text,
        gender = user.voice if user.voice in ["male", "female"] else "male",
        output_folder="/data/audio/voice_notifications"
    )

    db = SessionLocal()
    notification = NotificationLog(
        user_id=user.id,
        content=text,
        type="voice_nudge",
        audio_file=os.path.join("voice_notifications", os.path.basename(audio_path)),
        created_at=datetime.utcnow()
    )
    try:
        db.add(notification)
        db.commit()
    except Exception as e:
        print(f"DB commit failed: {e}")
        if os.path.exists(audio_path):
            os.remove(audio_path)
        raise

    print(f"[VOICE NUDGE] Created for {user.name}")
    print(f"[VOICE AUDIO]: {audio_path}")

def store_in_chat_prompt(user, goals, habits):
    """
    Stores a prompt message to show in chat when the user opens the app.
    """
    text = build_nudge_text(user, goals, habits)
    db = SessionLocal()
    message = Message(
        user_id=user.id,
        role="assistant",
        content=text,
        is_prompt=True,
        metadata="in_chat"
    )
    db.add(message)
    db.commit()
    print(f"[IN-CHAT PROMPT] stored for {user.name}")

def store_local_notification(user, goals, habits):
    """
    Stores a notification record for showing as a local notification in the app.
    """
    text = build_nudge_text(user, goals, habits)
    db = SessionLocal()
    notification = NotificationLog(
        user_id=user.id,
        content=text,
        type="local_notification",
        created_at=datetime.utcnow()
    )
    db.add(notification)
    db.commit()
    print(f"[LOCAL NOTIFICATION] stored for {user.name}")

def build_nudge_text(user, goals, habits):
    """
    Assembles the friendly text to deliver.
    """
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
