from app.database import SessionLocal
from app.models.message_model import Message
from app.models.user import User
from app.utils.tier_logic import get_user_max_message_retention_days
from datetime import datetime, timedelta

def delete_old_unimportant_messages():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        total_deleted = 0

        for user in users:
            retention_days = get_user_max_message_retention_days(user)
            threshold = datetime.utcnow() - timedelta(days=retention_days)

            deleted = db.query(Message).filter(
                Message.user_id == user.id,
                Message.important == False,
                Message.timestamp < threshold
            ).delete()
            total_deleted += deleted

        db.commit()
        print(f"✅ Deleted {total_deleted} old unimportant messages.")
    except Exception as e:
        print(f"❌ Error deleting messages: {e}")
    finally:
        db.close()
