# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.



from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.models.database import Base
from datetime import datetime

class UserTraitSummary(Base):
    __tablename__ = "user_trait_summaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    trait_type = Column(String)
    trait_value = Column(String)
    frequency = Column(Integer)
    from_date = Column(DateTime)
    to_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
