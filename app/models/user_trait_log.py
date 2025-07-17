# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.



from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base

class UserTraitLog(Base):
    __tablename__ = "user_trait_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    trait_type = Column(String, index=True)  # e.g. "emotion", "habit_streak", "tone"
    trait_value = Column(String)
    source = Column(String, default="neura")  # e.g. "checkin", "chat", "voice"
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="trait_logs")
