# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base

class UserUsageStat(Base):
    __tablename__ = "user_usage_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    usage_type = Column(String, index=True)  # e.g. "qna_summary", "goal", "habit"
    count = Column(Integer, default=0)
    last_used = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="usage_stats")

    __table_args__ = (UniqueConstraint("user_id", "usage_type", name="uq_user_usage_type"),)
