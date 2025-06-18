from sqlalchemy.orm import Session
from datetime import datetime
from app.models.database import SessionLocal
from app.models.task_reminder_model import TaskReminder

def delete_expired_task_reminders():
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        expired = db.query(TaskReminder).filter(TaskReminder.remind_at < now).all()
        for reminder in expired:
            db.delete(reminder)
        db.commit()
        if expired:
            print(f"[Scheduler] Deleted {len(expired)} expired task reminder.")
    finally:
        db.close()
