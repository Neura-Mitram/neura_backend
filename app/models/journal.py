# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base
from app.utils.encryption import EncryptedTypeHybrid  # 🔐 Encryption utils

class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    entry_text = Column(EncryptedTypeHybrid, nullable=False)  # 🔐 Encrypted
    ai_insight = Column(EncryptedTypeHybrid, nullable=True)  # 🔐 Encrypted

    timestamp = Column(DateTime, default=datetime.utcnow)
    emotion_label = Column(String, default="joy")  # e.g., happy, sad, anxious, angry

    user = relationship("User", back_populates="journal_entries")
