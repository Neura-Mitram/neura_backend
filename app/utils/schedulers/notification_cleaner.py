from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.notification import NotificationLog

def delete_old_notification_logs():
    db: Session = SessionLocal()
    try:
        threshold_date = datetime.utcnow() - timedelta(days=30)
        old_logs = db.query(NotificationLog).filter(NotificationLog.timestamp < threshold_date).all()

        deleted_count = 0
        for log in old_logs:
            db.delete(log)
            deleted_count += 1

        db.commit()
        if deleted_count:
            print(f"[Cron] Deleted {deleted_count} old notification logs.")

    except Exception as e:
        print(f"[Cron] Error deleting old notification logs: {e}")

    finally:
        db.close()
