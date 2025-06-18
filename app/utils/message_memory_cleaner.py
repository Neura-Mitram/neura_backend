from app.models.database import SessionLocal
from app.models.message_model import Message
from datetime import datetime, timedelta

def delete_old_unimportant_messages():
    db = SessionLocal()
    try:
        threshold = datetime.utcnow() - timedelta(days=2)
        deleted = db.query(Message).filter(
            Message.important == False,
            Message.timestamp < threshold
        ).delete()
        db.commit()
        return f"Deleted {deleted} old unimportant messages."
    finally:
        db.close()
