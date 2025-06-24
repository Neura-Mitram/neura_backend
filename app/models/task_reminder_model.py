from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.database import Base
from datetime import datetime

class TaskReminder(Base):
    __tablename__ = "task_reminders"  # ✅ FIXED

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    due_time = Column(DateTime, nullable=False, index=True)
    is_recurring = Column(Boolean, default=False)
    recurrence_type = Column(String, nullable=True)  # 'daily', 'weekly', etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    completed = Column(Boolean, default=False)

    user = relationship("User", back_populates="task_reminders")
