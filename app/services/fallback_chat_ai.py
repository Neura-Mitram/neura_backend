# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.user import User
from app.models.message_model import Message
from app.utils.ai_engine import generate_ai_reply
from app.utils.auth_utils import build_chat_history
from app.utils.red_flag_utils import detect_red_flag
from app.utils.prompt_templates import red_flag_response, creator_info_response
from app.services.emotion_tone_updater import update_emotion_status

ASSISTANT_NAME = "Neura"

async def handle_chat_fallback(
    db: Session,
    user: User,
    user_message: str,
    is_important: bool,
    conversation_id: int
):
    """
    Generates a friendly fallback chat reply and saves to memory.
    """

    # 🚩 Check for red flags
    red_flag = detect_red_flag(user_message)
    if red_flag == "code":
        return {
            "reply": red_flag_response("code or internal details"),
            "memory_enabled": user.memory_enabled,
            "important": is_important,
            "messages_used_this_month": user.monthly_gpt_count
        }
    if red_flag == "creator":
        return {
            "reply": creator_info_response(),
            "memory_enabled": user.memory_enabled,
            "important": is_important,
            "messages_used_this_month": user.monthly_gpt_count
        }

    # ✅ Update emotion
    emotion_label = await update_emotion_status(user, user_message, db)

    # 🧠 Build context if memory enabled
    if user.memory_enabled:
        chat_history = build_chat_history(db, user.id, conversation_id)
        full_prompt = f"{chat_history}User: {user_message}\n{ASSISTANT_NAME}:"
    else:
        full_prompt = user_message

    # 🤖 Generate reply
    assistant_reply = generate_ai_reply(full_prompt)

    # 💾 Save both messages
    if user.memory_enabled:
        db.add_all([
            Message(
                user_id=user.id,
                conversation_id=conversation_id,
                sender="user",
                message=user_message,
                important=is_important
            ),
            Message(
                user_id=user.id,
                conversation_id=conversation_id,
                sender="assistant",
                message=assistant_reply,
                important=False
            ),
        ])

    # ✅ Increment monthly count
    user.monthly_gpt_count += 1
    db.commit()

    return {
        "reply": assistant_reply,
        "memory_enabled": user.memory_enabled,
        "important": is_important,
        "messages_used_this_month": user.monthly_gpt_count,
        "emotion": emotion_label
    }
