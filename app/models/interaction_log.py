# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base  # ✅ absolute import
from app.utils.encryption import EncryptedTypeHybrid # 🔐 Encryption utils

class InteractionLog(Base):
    __tablename__ = "interaction_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    # 🔐 Encrypted fields
    source_app = Column(EncryptedTypeHybrid, nullable=True)  # e.g., WhatsApp, Gmail
    intent = Column(EncryptedTypeHybrid, nullable=True)  # e.g., checkin, goal_list
    content = Column(EncryptedTypeHybrid, nullable=True)  # Text or voice content

    # Add this inside the InteractionLog class
    emotion = Column(String, nullable=True)  # e.g., happy, sad, anxious

    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="interaction_logs")
