# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional
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
    preferred_lang = Column(String, default="en")  # e.g., "en", "hi", "bn"

    # ✅ For FCM _ Cloud Firebase Token
    fcm_token: Optional[str] = Column(String)

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
    interaction_logs = relationship("InteractionLog", back_populates="user", cascade="all, delete-orphan")
    journal_entries = relationship("JournalEntry", back_populates="user", cascade="all, delete-orphan")
    daily_checkins = relationship("DailyCheckin", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("NotificationLog", back_populates="user", cascade="all, delete-orphan")
    generated_audio = relationship("GeneratedAudio", back_populates="user", cascade="all, delete-orphan")
    goal_entries = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    habit_entries = relationship("Habit", back_populates="user", cascade="all, delete-orphan")
    trait_logs = relationship("UserTraitLog", back_populates="user", cascade="all, delete-orphan")
    usage_stats = relationship("UserUsageStat", back_populates="user", cascade="all, delete-orphan")
    traits = relationship("UserTraits", back_populates="user", cascade="all, delete-orphan")

    # ✅ Personalization
    goal_focus = Column(String, default="balance")
    personality_mode = Column(String, default="default")
    emotion_status = Column(String, default="joy")

    # ✅ Smart Persona Usage Counters
    journal_usage = Column(Integer, default=0)
    habit_usage = Column(Integer, default=0)
    goal_usage = Column(Integer, default=0)
    checkin_usage = Column(Integer, default=0)
    search_usage = Column(Integer, default=0)

    # ✅ Private mode
    is_private = Column(Boolean, default=False)
    last_private_on = Column(DateTime, nullable=True)

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

    # ✅ User Lat,Long & SOS
    last_lat = Column(Float, nullable=True)  # User's last known latitude
    last_lon = Column(Float, nullable=True)  # User's last known longitude
    safety_alert_optin = Column(Boolean, default=True)  # Whether user wants to get SOS alerts

    # ✅ New ambient context fields
    last_app_used = Column(String, nullable=True)  # e.g., "Spotify", "Gmail"
    battery_level = Column(Integer, nullable=True)  # e.g., 85
    network_type = Column(String, nullable=True)  # "wifi", "mobile", etc.
    local_time_snapshot = Column(String, nullable=True)  # "HH:MM"
    last_hourly_nudge_sent = Column(DateTime, nullable=True)

    # ✅ For Travel Tip
    last_travel_tip_sent = Column(DateTime, nullable=True)
    active_mode = Column(String, default=None)  # e.g., 'interpreter', 'private', etc.

    def __repr__(self):
        return f"<User id={self.id} tier={self.tier.value} personality={self.personality_mode}>"
