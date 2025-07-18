# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from app.models.database import Base
from app.utils.encryption import EncryptedTypeHybrid  # 🔐 Encryption wrapper

class SOSLog(Base):
    __tablename__ = "sos_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    message = Column(EncryptedTypeHybrid, nullable=True)     # 🔐 Sensitive input
    emotion = Column(String, nullable=True)                   # OK as string
    location = Column(EncryptedTypeHybrid, nullable=True)     # 🔐 Optional — could be sensitive

    timestamp = Column(DateTime, default=datetime.utcnow)


class UnsafeAreaReport(Base):
    __tablename__ = "unsafe_area_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    location = Column(EncryptedTypeHybrid, nullable=True)      # 🔐 User-entered
    reason = Column(String, nullable=False)                    # e.g. "dark area" — OK to keep plain
    description = Column(EncryptedTypeHybrid, nullable=True)   # 🔐 User description

    timestamp = Column(DateTime, default=datetime.utcnow)
