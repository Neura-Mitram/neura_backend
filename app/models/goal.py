# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
from app.models.database import Base
from app.utils.encryption import EncryptedTypeHybrid # 🔐 Encryption utils

class Goal(Base):
    __tablename__ = "goal_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    goal_text = Column(EncryptedTypeHybrid, nullable=False)     # 🔐 Encrypted
    ai_insight = Column(EncryptedTypeHybrid, nullable=True)     # 🔐 Encrypted

    deadline = Column(DateTime, nullable=True)
    status = Column(Text, default="active")
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    progress_percent = Column(Integer, default=0)
    last_progress_update = Column(DateTime, nullable=True)
    progress_streak_count = Column(Integer, default=0)

    emotion_label = Column(String, default="joy")

    user = relationship("User", back_populates="goal_entries")

    def __repr__(self):
        return f"<Goal id={self.id} status={self.status} progress={self.progress_percent}%>"
