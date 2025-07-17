# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base
from app.utils.encryption import EncryptedTypeHybrid  # 🔐 Encryption utils

class MoodLog(Base):
    __tablename__ = "mood_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mood_rating = Column(Integer, nullable=False)
    energy_level = Column(Integer, nullable=True)

    note = Column(EncryptedTypeHybrid, nullable=True)  # 🔐 Encrypted
    ai_feedback = Column(EncryptedTypeHybrid, nullable=True)  # 🔐 Encrypted

    emotion_label = Column(String, default="joy")
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="mood_logs")
