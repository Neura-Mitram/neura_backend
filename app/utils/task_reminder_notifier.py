import os
import logging
from datetime import datetime, timedelta
from pytz import timezone
from app.models.database import SessionLocal
from app.models.task_reminder_model import TaskReminder
from app.models.user_model import User
from app.utils.audio_processor import synthesize_voice

# ✅ Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def notify_due_reminders() -> None:
    """
    Checks for due task reminders and generates voice notifications.
    Marks one-time tasks as completed or reschedules recurring ones.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone("Asia/Kolkata")).replace(second=0, microsecond=0)

        due_reminders = db.query(TaskReminder).filter(
            TaskReminder.due_time <= now,
            TaskReminder.completed == False
        ).all()

        logging.info(f"🔔 Found {len(due_reminders)} due reminders at {now.isoformat()}")

        for reminder in due_reminders:
            user = db.query(User).filter(User.id == reminder.user_id).first()
            if not user:
                logging.warning(f"⚠️ User not found for reminder ID {reminder.id}")
                continue

            reminder_text = (
                f"Hello {user.name or 'User'}, this is your reminder: "
                f"{reminder.title}. The task is due now."
            )

            logging.info(f"🔔 {reminder_text}")

            try:
                # 🔊 Generate voice reminder
                gender = user.voice_gender or "male"
                audio_path = synthesize_voice(reminder_text, gender=gender)
                logging.info(f"🎧 Audio saved at: /get-temp-audio/{os.path.basename(audio_path)}")
            except Exception as e:
                logging.error(f"❌ Voice generation failed for reminder {reminder.id}: {e}")
                continue

            # ✅ Mark or reschedule
            if not reminder.is_recurring:
                reminder.completed = True
            else:
                if reminder.recurrence_type == "daily":
                    reminder.due_time += timedelta(days=1)
                elif reminder.recurrence_type == "weekly":
                    reminder.due_time += timedelta(weeks=1)

        db.commit()

    except Exception as e:
        logging.error(f"[ReminderNotifier] Error: {e}")
    finally:
        db.close()
