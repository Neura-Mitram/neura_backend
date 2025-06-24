from fastapi import HTTPException, Header
from typing import Union
from sqlalchemy.orm import Session  # ✅ Needed for type hinting in get_memory_messages
from app.utils.jwt_utils import verify_access_token
from app.models.message_model import Message  # ✅ REQUIRED: You're using Message in queries


# ✅ Token-user matching guard
def ensure_token_user_match(token_sub: str, input_id: Union[str, int]):
    if str(token_sub) != str(input_id):
        raise HTTPException(status_code=401, detail="Token/user mismatch")


# ✅ Chat history builder for GPT context
def build_chat_history(db: Session, user_id: int, limit: int = 10) -> str:
    past_msgs = (
        db.query(Message)
        .filter(Message.user_id == user_id)
        .order_by(Message.timestamp.desc())
        .limit(limit)
        .all()
    )
    past_msgs.reverse()

    history = ""
    for msg in past_msgs:
        role = "User" if msg.sender == "user" else "Neura"
        history += f"{role}: {msg.message}\n"
    return history


# ✅ Get memory messages for /memory-log
def get_memory_messages(db: Session, user_id: int, limit: int = 10):
    msgs = (
        db.query(Message)
        .filter(Message.user_id == user_id)
        .order_by(Message.timestamp.desc())
        .limit(limit)
        .all()
    )
    msgs.reverse()
    return msgs


# ✅ Dependency to extract token payload
def require_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    token = authorization.replace("Bearer ", "")
    return verify_access_token(token)
