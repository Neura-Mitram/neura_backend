from sqlalchemy import Column, Integer, Text, Date, ForeignKey
from app.models.database import Base
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
