# app/models/goal.py

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base

class Goal(Base):
    __tablename__ = "goal_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    goal_text = Column(Text, nullable=False)
    ai_insight = Column(Text, nullable=True)
    deadline = Column(DateTime, nullable=True)
    status = Column(Text, default="active")
    completed_at = Column(DateTime, nullable=True)  # ✅ Complete mark
    created_at = Column(DateTime, default=datetime.utcnow)

    # ✅ NEW FIELDS
    progress_percent = Column(Integer, default=0)
    last_progress_update = Column(DateTime, nullable=True)
    progress_streak_count = Column(Integer, default=0)

    emotion_label = Column(String, default="neutral")  # e.g., happy, sad, anxious, angry

    user = relationship("User", back_populates="goal_entries")

    def __repr__(self):
        return f"<Goal id={self.id} status={self.status} progress={self.progress_percent}%>"