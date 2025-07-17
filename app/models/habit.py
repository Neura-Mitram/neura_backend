# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
from app.models.database import Base
from app.utils.encryption import EncryptedTypeHybrid  # 🔐

class Habit(Base):
    __tablename__ = "habit_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    habit_name = Column(EncryptedTypeHybrid, nullable=False)  # 🔐
    motivation_tip = Column(EncryptedTypeHybrid, nullable=True)  # 🔐

    frequency = Column(String, nullable=False)  # 'daily', 'weekly', etc.
    streak_count = Column(Integer, default=0)
    last_completed = Column(DateTime, nullable=True)
    status = Column(Text, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    emotion_label = Column(String, default="joy")

    user = relationship("User", back_populates="habit_entries")