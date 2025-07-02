from datetime import datetime, timedelta
from app.models.database import SessionLocal
from app.models.daily_checkin import DailyCheckin

def clean_old_checkins():
    db = SessionLocal()
    try:
        cutoff_date = (datetime.now() - timedelta(days=90)).date().isoformat()
        deleted = db.query(DailyCheckin).filter(DailyCheckin.date < cutoff_date).delete()
        db.commit()
        print(f"[AutoClean] Deleted {deleted} old check-ins older than {cutoff_date}")
    except Exception as e:
        print(f"[AutoClean] Error cleaning check-ins: {str(e)}")
    finally:
        db.close()
