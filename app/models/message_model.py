from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.user import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender = Column(String, nullable=False)  # 'user' or 'assistant'
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    important = Column(Boolean, default=False)  # ✅ New field
    conversation_id = Column(Integer, default=1, index=True)
    emotion_label = Column(String, default="neutral", index=True)

    user = relationship("User", backref="messages")

    __table_args__ = (
            Index(
                "ix_user_conversation_timestamp",
                "user_id",
                "conversation_id",
                "timestamp"
            ),
        )