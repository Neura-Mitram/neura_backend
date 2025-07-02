# app/routers/emotion_router.py

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from datetime import datetime
from collections import Counter

from app.utils.auth_utils import require_token
from app.models.message_model import Message
from app.utils.rate_limit_utils import get_tier_limit, limiter

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/emotion-summary")
@limiter.limit(get_tier_limit)
async def emotion_summary(
    request: Request,
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    """
    Returns counts of each emotion label over the given date range.
    """

    # Validate dates
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    if end < start:
        raise HTTPException(status_code=400, detail="End date cannot be before start date.")

    user_id = user_data["sub"]

    # Query messages
    messages = (
        db.query(Message)
        .filter(Message.user_id == user_id)
        .filter(Message.timestamp >= start)
        .filter(Message.timestamp <= end)
        .all()
    )

    # Count occurrences
    emotion_counter = Counter()
    for m in messages:
        emotion = (m.emotion_label or "unknown").lower().strip()
        emotion_counter[emotion] += 1

    summary = [{"emotion": k, "count": v} for k, v in emotion_counter.items()]

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_records": len(messages),
        "summary": summary
    }
