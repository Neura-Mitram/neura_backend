# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import HTTPException, Header
from typing import Union
from sqlalchemy.orm import Session  # ✅ Needed for type hinting in get_memory_messages
from app.utils.jwt_utils import verify_access_token
from app.models.message_model import Message  # ✅ REQUIRED: You're using Message in queries
from app.utils.ai_engine import generate_ai_reply

# ✅ Token-user matching guard
def ensure_token_user_match(token_sub: str, input_id: Union[str, int]):
    if str(token_sub) != str(input_id):
        raise HTTPException(status_code=401, detail="Token/user mismatch")


# ✅ Dependency to extract token payload
def require_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    token = authorization.replace("Bearer ", "")
    return verify_access_token(token)


def build_chat_history(db, user_id, conversation_id, recent_count):
    """
    Builds chat history:
    - Summarizes older messages
    - Includes last N messages verbatim
    """
    all_msgs = (
        db.query(Message)
        .filter_by(user_id=user_id, conversation_id=conversation_id)
        .order_by(Message.timestamp)
        .all()
    )

    if not all_msgs:
        return ""

    # Split recent and older
    recent_msgs = all_msgs[-recent_count:]
    older_msgs = all_msgs[:-recent_count]

    # Summarize older user messages
    summary = ""
    if older_msgs:
        joined = " ".join(
            m.message for m in older_msgs if m.sender == "user"
        )
        if joined.strip():
            summary = summarize_messages(joined)

    # Build final prompt
    history = ""
    if summary:
        history += f"Summary of earlier conversation:\n{summary}\n\n"

    for m in recent_msgs:
        prefix = "User:" if m.sender == "user" else "Assistant:"
        history += f"{prefix} {m.message}\n"

    return history

def summarize_messages(text: str) -> str:
    prompt = f"""
You are a helpful assistant.

Summarize the following conversation in 3-4 sentences, capturing key points:

{text}
"""
    return generate_ai_reply(prompt).strip()



