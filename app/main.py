# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi.middleware.cors import CORSMiddleware


import os

from app.models.database import engine
from app.models import database
from app.models import *  # registers all models

from app.routers import chat_router, anonymous_router
from app.routers import event_router
from app.routers import device_router
from app.routers import profile_summary_router
from app.routers import emotion_router
from app.routers import memory_router
from app.routers import safety_router
from app.routers import wakeword_router
from app.routers import neura_private_router
from app.routers import stream_router
from app.routers import healthz_router

# 🕛 Schedulers import
from app.utils.schedulers.run_all_cleanups import run_all_cleanups
from app.utils.schedulers.cron.reset_usage_counters import reset_all_usage_counters
from app.utils.schedulers.cron.private_mode_resetter_cron  import reset_expired_private_modes
from app.utils.schedulers.cron.morning_news_cron import run_morning_news_cron
from app.utils.schedulers.cron.weekly_trait_summary_cron import weekly_trait_summaries_cron
from app.utils.schedulers.cron.trait_compression_cron import compress_old_traits

from app.services.nudge_service import process_nudges
from app.services.hourly_notifier import hourly_notify_users

from pytz import timezone as pytz_timezone  # ✅ Rename to avoid collision
IST = pytz_timezone("Asia/Kolkata")         # ✅ Create pytz-compatible timezone object


from app.utils.rate_limit_utils import limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.responses import JSONResponse

from pathlib import Path

import requests
ip = requests.get("https://api64.ipify.org").text
print("Hugging Face Space Public Outbound IP:", ip)


# Create DB tables in one go
database.Base.metadata.create_all(bind=database.engine)

# Scheduler setup
scheduler = BackgroundScheduler(job_defaults={"misfire_grace_time": 60})

@asynccontextmanager
async def lifespan(app: FastAPI):

    # 🕛 Clean every day at 2 AM
    scheduler.add_job(run_all_cleanups, "cron", hour=2, minute=0, timezone=IST)

    # 🗓️ Reset usage counters monthly on the 1st at 3 AM
    scheduler.add_job(reset_all_usage_counters, "cron", day=1, hour=3, minute=0, timezone=IST)

    # 🕛 Runs every 2 hour
    scheduler.add_job(process_nudges, trigger="cron", hour="*/2", minute=30, timezone=IST)

    # 🕛 Runs every 1 hour
    scheduler.add_job(hourly_notify_users, trigger="cron", minute=0, timezone=IST)

    # 🕛 Runs every day at 8:00 AM for news
    scheduler.add_job(run_morning_news_cron, "cron", hour=8, minute=0, timezone=IST)

    # 🗓️ Runs every Sunday at 9 AM
    scheduler.add_job(weekly_trait_summaries_cron, "cron", day_of_week="sun", hour=9, minute=0, timezone="Asia/Kolkata")

    # 🗓️ Run on 1st of every month at 3:00 AM
    scheduler.add_job(compress_old_traits, "cron", day=1, hour=3, minute=0, timezone="Asia/Kolkata")

    # 🔁 Runs every 10 minutes to auto-resume private mode
    scheduler.add_job(reset_expired_private_modes, trigger="interval", minutes=10, timezone=IST)


    scheduler.start()
    yield
    scheduler.shutdown()

# Create FastAPI app with lifespan
app = FastAPI(
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    title="Neura Smart Assistant API",
    description="Voice & Text AI backend",
    version="1.0"
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)



wake_audio_path = Path("/tmp/wake_audio")
os.makedirs(wake_audio_path, exist_ok=True)

app.mount("/wake_audio", StaticFiles(directory=wake_audio_path), name="wake_audio")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use ["http://localhost:3000"] in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(chat_router.router)
app.include_router(anonymous_router.router)
app.include_router(event_router.router)
app.include_router(device_router.router)
app.include_router(profile_summary_router.router)
app.include_router(memory_router.router)
app.include_router(emotion_router.router)
app.include_router(safety_router.router)
app.include_router(wakeword_router.router)
app.include_router(neura_private_router.router)
app.include_router(stream_router.router)
app.include_router(healthz_router.router)


# ---------------------- ADDING EXCEPTION HANDLER ----------------------
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please slow down."}
    )

@app.get("/")
def read_root():
    return {
        "message": "👋 Welcome to Neura – Mitram",
        "description": "This API powers Neura's intelligent voice and text interactions and provides an open foundation for proactive personal assistant experiences.",
        "copyright": "© 2025 Shiladitya Mallick",
        "license": "MIT License - See LICENSE file for details."
    }


@app.get("/health", tags=["Infra"])
def health_check():
    return {"status": "ok"}

