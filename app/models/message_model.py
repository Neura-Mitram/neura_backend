# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base
from app.utils.encryption import EncryptedTypeHybrid  # ✅ Import encryption


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender = Column(String, nullable=False)  # 'user' or 'assistant'

    message = Column(EncryptedTypeHybrid, nullable=True)  # ✅ Encrypted message

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    important = Column(Boolean, default=False)
    conversation_id = Column(Integer, default=1, index=True)
    emotion_label = Column(String, index=True)

    user = relationship("User", backref="messages")

    __table_args__ = (
        Index("ix_user_conversation_timestamp", "user_id", "conversation_id", "timestamp"),
    )
