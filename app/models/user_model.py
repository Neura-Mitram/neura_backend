from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=True)
    name = Column(String, default="")
    ai_name = Column(String, default="NeuraAI")
    voice = Column(String, default="male")  # Options: 'male' or 'female'
    tier = Column(String, default="Tier 1")    # Tier: 'Tier 1', 'Tier 2', 'Tier 3'
    memory_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # ✅ Anonymous login tracking
    temp_uid = Column(String, nullable=True, unique=True)  # Unique device ID
    trial_start = Column(DateTime, nullable=True)  # Trial period start
    # ✅ Is verified
    is_verified = Column(Boolean, default=False)

    payment_key = Column(String, nullable=True)

    # 🔥 NEW: Track GPT usage
    monthly_gpt_count = Column(Integer, default=0)
    last_gpt_reset = Column(DateTime, default=datetime.utcnow)

    # 🔉 Voice chat usage tracking
    monthly_voice_count = Column(Integer, default=0)
    last_voice_reset = Column(DateTime, default=datetime.utcnow)

    # 🔥 NEW: Task Reminder usage
    task_reminders = relationship("TaskReminder", back_populates="user", cascade="all, delete-orphan")



