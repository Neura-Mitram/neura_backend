from datetime import datetime
from sqlalchemy.orm import Session
from app.models.interaction_log import InteractionLog
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

def track_intent_usage(db: Session, user: User, intent_name: str, message: str = ""):
    """
    Logs user intent usage to InteractionLog.
    """
    try:
        log = InteractionLog(
            user_id=user.id,
            intent=intent_name,
            content=message,
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
        return True
    except Exception as e:
        logger.warning(f"⚠️ Intent tracking failed for '{intent_name}': {e}")
        return False
