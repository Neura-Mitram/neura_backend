# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from app.models.message_model import Message
from app.utils.tier_logic import get_max_memory_messages
from sqlalchemy import desc
from sqlalchemy.orm import Session
from app.models.user import User, TierLevel
from app.services.emotion_tone_updater import infer_emotion_label

def save_user_message(
    db: Session,
    user: User,
    message_text: str,
    conversation_id: int = 1,
    sender: str = "user",
    emotion_label=None
):
    """
    Saves a message (user or assistant) to the messages table.
    Also enforces tier-based memory limit (on user messages only).
    """
    if not user.memory_enabled:
        return

    # ✅ Emotion inference only for user messages, if not passed explicitly
    if sender == "user" and emotion_label is None:
          emotion_label = infer_emotion_label(message_text)

    db.add(Message(
        user_id=user.id,
        conversation_id=conversation_id,
        sender=sender,
        message=message_text,
        important=False,
        emotion_label=emotion_label
    ))
    db.commit()

    # Only prune user messages
    if sender == "user":
        tier_limit = get_max_memory_messages(user.tier or TierLevel.free)
        messages = (
            db.query(Message)
            .filter(Message.user_id == user.id, Message.sender == "user")
            .order_by(desc(Message.timestamp))
            .all()
        )
        if len(messages) > tier_limit:
            to_delete = messages[tier_limit:]
            for msg in to_delete:
                db.delete(msg)
            db.commit()
