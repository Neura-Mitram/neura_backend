from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.models.database import SessionLocal

from app.models.user_model import User
from app.models.message_model import Message
from app.models.task_reminder_model import TaskReminder

from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import IntegrityError
from app.utils.tier_check import get_monthly_limit
from app.utils.ai_engine import generate_ai_reply
from datetime import datetime


router = APIRouter()


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TaskReminderCreate(BaseModel):
     user_id: int
     title: str
     due_time: datetime
     recurrence_type: str = "once"  # Options: once, daily, weekly

class TaskReminderUpdate(BaseModel):
    id: int
    title: str
    datetime: datetime
    repeat: str  # "once", "daily", "weekly"


class ChatInput(BaseModel):
    user_id: int
    message: str

@router.post("/chat")
def chat_with_aditya(data: ChatInput, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ✨ Detect if user message is important (basic keyword detection)
    important_keywords = ["remember", "goal", "habit", "remind", "dream", "mission"]
    is_important = any(word in data.message.lower() for word in important_keywords)

    # 🔁 Auto-reset GPT usage counter if month has changed
    now = datetime.utcnow()
    if user.last_gpt_reset.month != now.month or user.last_gpt_reset.year != now.year:
        user.monthly_gpt_count = 0
        user.last_gpt_reset = now

    # 🔒 Enforce GPT monthly tier limit
    monthly_limit = get_monthly_limit(user.tier)
    if user.monthly_gpt_count >= monthly_limit:
        db.commit()
        return {
            "reply": f"⚠️ You've used your {monthly_limit} GPT messages for {user.tier} this month. Upgrade your plan to get more access.",
            "memory_enabled": user.memory_enabled,
            "important": is_important,
            "messages_used_this_month": user.monthly_gpt_count,
            "messages_remaining": 0
        }

    # 🧠 Save user message if memory is enabled
    if user.memory_enabled:
        user_msg = Message(
            user_id=user.id,
            sender="user",
            message=data.message,
            important=is_important
        )
        db.add(user_msg)

    # 🧠 Use memory context if enabled
    chat_history = ""
    if user.memory_enabled:
        past_msgs = db.query(Message) \
            .filter(Message.user_id == user.id) \
            .order_by(Message.timestamp.desc()) \
            .limit(10).all()
        past_msgs.reverse()

        for msg in past_msgs:
            role = "User" if msg.sender == "user" else "Aditya"
            chat_history += f"{role}: {msg.message}\n"
        full_prompt = f"{chat_history}User: {data.message}\nAditya:"
    else:
        full_prompt = data.message

    # 🤖 Generate GPT reply
    assistant_reply = generate_ai_reply(full_prompt)

    # 🧠 Save assistant reply if memory is enabled
    if user.memory_enabled:
        ai_msg = Message(
            user_id=user.id,
            sender="assistant",
            message=assistant_reply,
            important=False
        )
        db.add(ai_msg)

    # ✅ Update GPT usage count
    user.monthly_gpt_count += 1
    db.commit()

    return {
        "reply": assistant_reply,
        "memory_enabled": user.memory_enabled,
        "important": is_important,
        "messages_used_this_month": user.monthly_gpt_count,
        "messages_remaining": monthly_limit - user.monthly_gpt_count
    }

@router.get("/memory-log")
def get_memory_log(user_id: int, limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.memory_enabled:
        return {"message": "Memory is disabled for this user."}

    messages = db.query(Message) \
        .filter(Message.user_id == user.id) \
        .order_by(Message.timestamp.desc()) \
        .limit(limit).all()

    messages.reverse()  # show oldest first for natural reading

    return {
        "email": user.email,
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

@router.post("/add-task-reminder")
def add_reminder(reminder_data: TaskReminderCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == reminder_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_reminder = TaskReminder(
        user_id=user.id,
        title=reminder_data.title,
        due_time=reminder_data.due_time,
        is_recurring=(reminder_data.recurrence_type != "once"),
        recurrence_type=reminder_data.recurrence_type
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

@router.get("/get-task-reminder")
def get_reminders(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reminders = db.query(TaskReminder).filter(TaskReminder.user_id == user.id).order_by(TaskReminder.due_time).all()

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

@router.delete("/delete-task-reminder/{task-reminder_id}")
def delete_reminder(task_reminder_id: int, db: Session = Depends(get_db)):
    reminder = db.query(TaskReminder).filter(TaskReminder.id == task_reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Task Reminder not found")

    db.delete(reminder)
    db.commit()
    return {"message": "Task Reminder deleted"}

@router.put("/update-task-reminder")
def update_reminder(reminder_data: TaskReminderUpdate, db: Session = Depends(get_db)):
    reminder = db.query(TaskReminder).filter(TaskReminder.id == reminder_data.id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Task Reminder not found")

    reminder.title = reminder_data.title
    reminder.due_time = reminder_data.datetime
    reminder.is_recurring = reminder_data.repeat != "once"
    reminder.recurrence_type = None if reminder_data.repeat == "once" else reminder_data.repeat

    db.commit()
    return {"message": "Task Reminder updated", "task-reminder": {
        "id": reminder.id,
        "title": reminder.title,
        "datetime": reminder.due_time,
        "repeat": reminder.recurrence_type or "once"
    }}
