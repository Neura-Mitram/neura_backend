from sqlalchemy import Column, Integer, String, Text
from models.database import Base
import datetime

class DailyCheckin(Base):
    __tablename__ = "daily_checkins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    date = Column(String, default=datetime.date.today().isoformat)
    mood_rating = Column(Integer, nullable=True)
    gratitude = Column(Text, nullable=True)
    thoughts = Column(Text, nullable=True)
    voice_summary = Column(Text, nullable=True)
