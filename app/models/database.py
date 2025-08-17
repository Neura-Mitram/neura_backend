# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ✅ Only load .env in local/dev
if os.environ.get("ENV") != "production":
    from dotenv import load_dotenv
    load_dotenv()

# ✅ Load required env variable
SQLALCHEMY_DATABASE_URL = os.environ["DATABASE_URL"]

# ✅ Engine with Supabase Transaction Pooler
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=10,          # Keep 10 connections open
    max_overflow=20,       # Allow 20 extra if under load
    pool_recycle=1800,     # Recycle every 30 mins
    pool_pre_ping=True     # Validate before using connection
)

# ✅ Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ✅ Base model
Base = declarative_base()
