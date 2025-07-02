# app/models/interaction_log.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base  # ✅ absolute import

class InteractionLog(Base):
    __tablename__ = "interaction_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    source_app = Column(String, nullable=True)  # WhatsApp, Gmail, etc.
    intent = Column(String, nullable=True)  # "checkin", "goal_list", etc.
    content = Column(Text, nullable=True)  # Text or voice content

    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="interaction_logs")
