from sqlalchemy.orm import Session
from datetime import datetime
from app.database import SessionLocal
from app.models.user import User

def reset_all_usage_counters():
    """
    Resets monthly GPT, voice, and creator counts for all users.
    Updates last_gpt_reset to now.
    """
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            user.monthly_gpt_count = 0
            user.monthly_voice_count = 0
            user.monthly_creator_count = 0
            user.last_gpt_reset = datetime.utcnow()
        db.commit()
        print("✅ All user usage counters have been reset.")
    except Exception as e:
        print(f"❌ Error resetting usage counters: {e}")
    finally:
        db.close()
