# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.models.database import Base
from app.utils.encryption import EncryptedTypeHybrid  # 🔐

class SOSContact(Base):
    __tablename__ = "sos_contacts"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)

    name = Column(EncryptedTypeHybrid, nullable=False)         # 🔐 Encrypted
    phone = Column(EncryptedTypeHybrid, nullable=False)        # 🔐 Encrypted
    relationship = Column(EncryptedTypeHybrid, nullable=True)  # 🔐 Optional encryption

    created_at = Column(DateTime, default=datetime.utcnow)
