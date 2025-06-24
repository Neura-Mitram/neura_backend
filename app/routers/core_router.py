from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from app.models.database import SessionLocal

from app.models.user_model import User, TierLevel
from app.utils.auth_utils import ensure_token_user_match, require_token, build_chat_history, get_memory_messages
from app.models.message_model import Message
from app.models.task_reminder_model import TaskReminder

from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import IntegrityError
from app.utils.tier_check import get_monthly_limit
from app.utils.ai_engine import generate_ai_reply
from datetime import datetime

from slowapi import Limiter
from slowapi.util import get_remote_address
from app.utils.rate_limit_utils import get_tier_limit


router = APIRouter()

ASSISTANT_NAME = "Neura"  # 🔄 changeable assistant name for prompt

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ChatRequest(BaseModel):
    user_id: int
    message: str

@limiter.limit(get_tier_limit)
@router.post("/chat-with-neura")
def chat_with_neura(payload: ChatRequest, db: Session = Depends(get_db), user_data: dict = Depends(require_token)):

    # 🔐 Ensure token-user match
    ensure_token_user_match(user_data["sub"], payload.user_id)

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 🧠 Tag important messages
    important_keywords = ["remember", "goal", "habit", "remind", "dream", "mission"]
    is_important = any(word in payload.message.lower() for word in important_keywords)

    # 📅 Monthly GPT count reset
    now = datetime.utcnow()
    if user.last_gpt_reset.month != now.month or user.last_gpt_reset.year != now.year:
        user.monthly_gpt_count = 0
        user.last_gpt_reset = now

    # ⛔ Tier check logic (combined for Free, separate for Basic/Pro)
    monthly_limit = get_monthly_limit(user.tier)

    if user.tier == TierLevel.free:
        total_usage = user.monthly_gpt_count + user.monthly_voice_count
        if total_usage >= monthly_limit:
            db.commit()
            return {
                "reply": f"⚠️ You've used your {monthly_limit} total messages this month. Upgrade your plan to get more access.",
                "memory_enabled": user.memory_enabled,
                "important": is_important,
                "messages_used_this_month": total_usage,
                "messages_remaining": 0
            }
    else:
        if user.monthly_gpt_count >= monthly_limit:
            db.commit()
            return {
                "reply": f"⚠️ You've used your {monthly_limit} text messages for {user.tier} this month. Upgrade your plan to get more access.",
                "memory_enabled": user.memory_enabled,
                "important": is_important,
                "messages_used_this_month": user.monthly_gpt_count,
                "messages_remaining": 0
            }

    # 💬 Save user message and build context
    if user.memory_enabled:
        db.add(Message(
            user_id=user.id,
            sender="user",
            message=payload.message,
            important=is_important
        ))
        chat_history = build_chat_history(db, user.id)
        full_prompt = f"{chat_history}User: {payload.message}\n{ASSISTANT_NAME}:"
    else:
        full_prompt = payload.message

    # 🤖 Generate response
    assistant_reply = generate_ai_reply(full_prompt)

    # 💬 Save assistant message
    if user.memory_enabled:
        db.add(Message(
            user_id=user.id,
            sender="assistant",
            message=assistant_reply,
            important=False
        ))

    # ✅ Update counter
    user.monthly_gpt_count += 1
    db.commit()

    return {
        "reply": assistant_reply,
        "memory_enabled": user.memory_enabled,
        "important": is_important,
        "messages_used_this_month": user.monthly_gpt_count,
        "messages_remaining": monthly_limit - user.monthly_gpt_count
    }


class MemoryLogRequest(BaseModel):
    user_id: int
    limit: int = 10

@limiter.limit(get_tier_limit)
@router.post("/memory-log")
def get_memory_log(payload: MemoryLogRequest, db: Session = Depends(get_db), user_data: dict = Depends(require_token)):
    ensure_token_user_match(user_data["sub"], payload.user_id)

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.memory_enabled:
        return {"message": "Memory is disabled for this user."}

    messages = get_memory_messages(db, user.id, payload.limit)

    return {
        "memory_enabled": user.memory_enabled,
        "messages": [
            {
                "sender": msg.sender,
                "message": msg.message,
                "timestamp": msg.timestamp.isoformat(),
                "important": msg.important
            } for msg in messages
        ]
    }


class AddTaskReminderRequest(BaseModel):
    user_id: int
    title: str
    due_time: datetime
    recurrence_type: str = "once"

@limiter.limit(get_tier_limit)
@router.post("/add-task-reminder")
def add_reminder(payload: AddTaskReminderRequest,  db: Session = Depends(get_db), user_data: dict = Depends(require_token)):
    ensure_token_user_match(user_data["sub"], payload.user_id)

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_reminder = TaskReminder(
        user_id=user.id,
        title=payload.title,
        due_time=payload.due_time,
        is_recurring=(payload.recurrence_type != "once"),
        recurrence_type=payload.recurrence_type
    )
    db.add(new_reminder)
    db.commit()
    db.refresh(new_reminder)

    return {"message": "Task Reminder created", "task-reminder": {
        "id": new_reminder.id,
        "title": new_reminder.title,
        "due_time": new_reminder.due_time,
        "recurrence_type": new_reminder.recurrence_type
    }}


class ListTaskReminderRequest(BaseModel):
    user_id: int

@limiter.limit(get_tier_limit)
@router.post("/list-task-reminders")
def list_task_reminders(payload: ListTaskReminderRequest, db: Session = Depends(get_db), user_data: dict = Depends(require_token)):
    ensure_token_user_match(user_data["sub"], payload.user_id)

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reminders = (
        db.query(TaskReminder)
        .filter(TaskReminder.user_id == user.id)
        .order_by(TaskReminder.due_time)
        .all()
    )

    return {
        "reminders": [
            {
                "id": r.id,
                "title": r.title,
                "due_time": r.due_time,
                "recurrence_type": r.recurrence_type
            } for r in reminders
        ]
    }


class ModifyTaskReminderRequest(BaseModel):
    id: int
    user_id: int
    title: str
    due_time: datetime
    recurrence_type: str = "once"

@limiter.limit(get_tier_limit)
@router.put("/modify-task-reminder")
def modify_task_reminder(payload: ModifyTaskReminderRequest, db: Session = Depends(get_db), user_data: dict = Depends(require_token)):
    ensure_token_user_match(user_data["sub"], payload.user_id)

    reminder = db.query(TaskReminder).filter(TaskReminder.id == payload.id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Task Reminder not found")

    # ✅ Check if reminder belongs to user from token
    if reminder.user_id != payload.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this reminder")

    reminder.title = payload.title
    reminder.due_time = payload.due_time
    reminder.is_recurring = payload.recurrence_type != "once"
    reminder.recurrence_type = None if payload.recurrence_type == "once" else payload.recurrence_type

    db.commit()

    return {"message": "Task Reminder modified", "task-reminder": {
        "id": reminder.id,
        "title": reminder.title,
        "datetime": reminder.due_time,
        "repeat": reminder.recurrence_type or "once"
    }}


class DeleteTaskReminderRequest(BaseModel):
    user_id: int
    task_reminder_id: int

@limiter.limit(get_tier_limit)
@router.delete("/delete-task-reminder")
def delete_reminder(payload: DeleteTaskReminderRequest,  db: Session = Depends(get_db), user_data: dict = Depends(require_token)):
    ensure_token_user_match(user_data["sub"], payload.user_id)

    reminder = db.query(TaskReminder).filter(TaskReminder.id == payload.task_reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Task Reminder not found")

    # ✅ Check if reminder belongs to user from token
    if reminder.user_id != payload.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this reminder")

    db.delete(reminder)
    db.commit()

    return {"message": "Task Reminder deleted"}