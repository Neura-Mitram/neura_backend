from sqlalchemy import Column, Integer, Text, Date, ForeignKey
from app.database import Base
import datetime

class DailyCheckin(Base):
    __tablename__ = "daily_checkins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, default=datetime.date.today())
    mood_rating = Column(Integer, nullable=True)
    gratitude = Column(Text, nullable=True)
    thoughts = Column(Text, nullable=True)
    voice_summary = Column(Text, nullable=True)

    emotion_label = Column(String, default="neutral")  # e.g., happy, sad, anxious, angry

    ai_insight = Column(Text, nullable=True)  # ✅ Add this line to store Mistral-generated insight

    user = relationship("User", back_populates="daily_checkins")

