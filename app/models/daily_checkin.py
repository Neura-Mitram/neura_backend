# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy import Column, Integer, Text, Date, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from app.models.database import Base
import datetime
from app.utils.encryption import EncryptedTypeHybrid  # 🔐

class DailyCheckin(Base):
    __tablename__ = "daily_checkins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, default=datetime.date.today())
    mood_rating = Column(Integer, nullable=True)
    # 🔐 Encrypted fields
    gratitude = Column(EncryptedTypeHybrid, nullable=True)
    thoughts = Column(EncryptedTypeHybrid, nullable=True)
    voice_summary = Column(EncryptedTypeHybrid, nullable=True)
    ai_insight = Column(EncryptedTypeHybrid, nullable=True)

    emotion_label = Column(String, default="joy")

    user = relationship("User", back_populates="daily_checkins")

