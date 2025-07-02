# app/models/habit

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Habit(Base):
    __tablename__ = "habit_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    habit_name = Column(String, nullable=False)
    frequency = Column(String, nullable=False)  # 'daily', 'weekly', etc.
    streak_count = Column(Integer, default=0)
    last_completed = Column(DateTime, nullable=True)
    motivation_tip = Column(String, nullable=True)
    status = Column(Text, default="active")
    # completed_at = Column(DateTime, nullable=True)  # ✅ Complete mark
    created_at = Column(DateTime, default=datetime.utcnow)
    emotion_label = Column(String, default="neutral")  # e.g., happy, sad, anxious, angry

    user = relationship("User", back_populates="habit_entries")
