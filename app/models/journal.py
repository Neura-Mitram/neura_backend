# app/models/journal_entry.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base

class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    entry_text = Column(Text, nullable=False)
    ai_insight = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    emotion_label = Column(String, default="neutral")  # e.g., happy, sad, anxious, angry

    user = relationship("User", back_populates="journal_entries")
