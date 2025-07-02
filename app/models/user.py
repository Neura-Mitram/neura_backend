from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum
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
    tier = Column(Enum(TierLevel), default=TierLevel.free)

    # ✅ Voice Nudges for sending update
    voice_nudges_enabled = Column(Boolean, default=True)
    push_notifications_enabled = Column(Boolean, default=True)
    nudge_frequency = Column(String, default="normal")  # low / normal / high
    nudge_last_sent = Column(DateTime, nullable=True)
    nudge_last_type = Column(String, nullable=True)  # voice / push / in_chat

    memory_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # ✅ Usage counters
    monthly_gpt_count = Column(Integer, default=0)        # Text usage counter
    monthly_voice_count = Column(Integer, default=0)      # Voice usage counter
    last_gpt_reset = Column(DateTime, default=datetime.utcnow)  # Last reset timestamp
    monthly_creator_count = Column(Integer, default=0)

    # ✅ Anonymous login tracking
    temp_uid = Column(String, nullable=True, unique=True, index=True)
    is_verified = Column(Boolean, default=False)

    # ✅ Relationships
    task_reminders = relationship("TaskReminder", back_populates="user", cascade="all, delete-orphan")
    audio_files = relationship("GeneratedAudio", back_populates="user", cascade="all, delete-orphan")
    interaction_logs = relationship("InteractionLog", back_populates="user", cascade="all, delete-orphan")
    journal_entries = relationship("JournalEntry", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("NotificationLog", back_populates="user", cascade="all, delete-orphan")

    # ✅ Personalization
    goal_focus = Column(String, default="balance")
    personality_mode = Column(String, default="default")
    emotion_status = Column(String, default="neutral")

    # ✅ Ambient Assistant
    hourly_ping_enabled = Column(Boolean, default=True)
    preferred_delivery_mode = Column(String, default="voice")
    instant_alerts_enabled = Column(Boolean, default=True)
    output_audio_mode = Column(String, default="speaker")
    monitored_keywords = Column(String, default="urgent,asap,payment")
    whitelisted_apps = Column(String, default="whatsapp,gmail")

    # ✅ Device Info
    device_type = Column(String, default="unknown")
    device_token = Column(String, nullable=True)
    os_version = Column(String, default="")
    last_active_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User id={self.id} tier={self.tier.value} personality={self.personality_mode}>"
