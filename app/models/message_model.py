from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .user_model import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender = Column(String)  # 'user' or 'assistant'
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    important = Column(Boolean, default=False)  # ✅ New field

    user = relationship("User", backref="messages")
