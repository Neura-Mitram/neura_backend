# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from app.models.message_model import Message

def save_user_message(db, user, message_text, conversation_id=1):
    """
    Saves a user message to the messages table.
    """
    if user.memory_enabled:
        db.add(Message(
            user_id=user.id,
            conversation_id=conversation_id,
            sender="user",
            message=message_text,
            important=False
        ))
        db.commit()
