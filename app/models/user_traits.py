# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base

class UserTraits(Base):
    __tablename__ = "user_traits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    trait_name = Column(String, index=True)  # e.g. "confident", "anxious"
    score = Column(Float, default=0.5)       # From 0.0 to 1.0
    source = Column(String, default="neura") # e.g. "checkin", "chat"
    last_updated = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="traits")

    __table_args__ = (UniqueConstraint("user_id", "trait_name", name="uq_user_trait"),)
