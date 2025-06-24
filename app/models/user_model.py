from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base
import enum


class TierLevel(enum.Enum):
    free = "free"
    basic = "basic"
    pro = "pro"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="")
    ai_name = Column(String, default="NeuraAI")
    voice = Column(String, default="male")  # Options: 'male' or 'female'
    tier = Column(Enum(TierLevel), default=TierLevel.free)    # Tier: 'free', 'basic', 'pro'
    memory_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # ✅ Anonymous login tracking
    temp_uid = Column(String, nullable=True, unique=True, index=True)  # Unique device ID
    trial_start = Column(DateTime, nullable=True)  # Trial period start
    # ✅ Is verified
    is_verified = Column(Boolean, default=False)

    payment_key = Column(String, nullable=True)

    # 🔥 Chat usage tracking
    monthly_gpt_count = Column(Integer, default=0)
    last_gpt_reset = Column(DateTime, default=datetime.utcnow)

    # 🔉 Voice chat usage tracking
    monthly_voice_count = Column(Integer, default=0)
    last_voice_reset = Column(DateTime, default=datetime.utcnow)

    # 🔥 NEW: Task Reminder usage
    task_reminders = relationship("TaskReminder", back_populates="user", cascade="all, delete-orphan")

    # NEW: Audio usage
    audio_files = relationship("GeneratedAudio", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} tier={self.tier.value}>"