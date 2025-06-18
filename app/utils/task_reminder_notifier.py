from models.database import SessionLocal
from app.models.task_reminder_model import TaskReminder
from models.user_model import User
from datetime import datetime, timedelta
from pytz import timezone
from app.utils.audio_processor import synthesize_voice
import os

def notify_due_reminders():
    db = SessionLocal()
    try:
        now = datetime.now(timezone("Asia/Kolkata")).replace(second=0, microsecond=0)

        due_reminders = db.query(TaskReminder).filter(
            TaskReminder.due_time <= now,
            TaskReminder.completed == False
        ).all()

        for reminder in due_reminders:
            user = db.query(User).filter(User.id == reminder.user_id).first()
            if not user:
                continue

            reminder_text = f"Hello {user.name or 'User'}, this is your reminder: {reminder.title}. The task is due now."
            print(f"🔔 {reminder_text}")

            # 🔊 Generate voice using Polly
            gender = user.voice_gender or "male"
            audio_path = synthesize_voice(reminder_text, gender=gender)

            print(f"🎧 Audio reminder saved at: /get-temp-audio/{os.path.basename(audio_path)}")

            # ✅ Mark as completed or reschedule
            if not reminder.is_recurring:
                reminder.completed = True
            else:
                if reminder.recurrence_type == "daily":
                    reminder.due_time += timedelta(days=1)
                elif reminder.recurrence_type == "weekly":
                    reminder.due_time += timedelta(weeks=1)

        db.commit()
    finally:
        db.close()
