# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

import os

from app.models.database import engine
from app.models import database
from app.models import *  # registers all models

from app.routers import chat_router, anonymous_router, voice_router
from app.routers import event_router
from app.routers import device_router  # ✅ Add this
from app.routers import profile_summary_router
from app.routers import emotion_router
from app.routers import alive_neura_tts_router

from app.services.nudge_service import process_nudges


from app.utils.schedulers.run_all_cleanups import run_all_cleanups
from app.utils.schedulers.reset_usage_counters import reset_all_usage_counters

from app.services.hourly_notifier import hourly_notify_users



from pytz import timezone  # ✅ use this for interval

from app.utils.rate_limit_utils import limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.responses import JSONResponse

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
    scheduler.add_job(run_all_cleanups, "cron", hour=2, minute=0, timezone=timezone("Asia/Kolkata"))

    # 🗓️ Reset usage counters monthly on the 1st at 3 AM
    scheduler.add_job(reset_all_usage_counters, "cron", day=1, hour=3, minute=0, timezone=timezone("Asia/Kolkata"))

    # 🗓️ Runs every 2 hour
    scheduler.add_job(process_nudges, trigger="cron", hour="*/2", minute=30, timezone=timezone("Asia/Kolkata"))

    # 🗓️ Runs every 1 hour
    scheduler.add_job(hourly_notify_users, trigger="cron", minute=0, timezone=timezone("Asia/Kolkata"))

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


# Ensure audio folder exists
os.makedirs("/data/audio/temp_audio", exist_ok=True)
os.makedirs("/data/audio/voice_chat", exist_ok=True)
os.makedirs("/data/audio/voice_notifications", exist_ok=True)

# Serve audio files from /get-audio/
# app.mount("/get-audio", StaticFiles(directory="/data/audio"), name="audio")

# Include routers
app.include_router(voice_router.router)
app.include_router(chat_router.router)
app.include_router(anonymous_router.router)
app.include_router(event_router.router)
app.include_router(device_router.router)  # ✅ Now /update-device is active
app.include_router(profile_summary_router.router)
app.include_router(emotion_router.router)
app.include_router(alive_neura_tts_router.router)





# ---------------------- ADDING EXCEPTION HANDLER ----------------------
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please slow down."}
    )

@app.get("/")
def read_root():
    return {"message": "Welcome to Neura - smart Assistant backend Live"
                       "Copyright (c) 2025 Shiladitya Mallick "
                       "This file is part of the Neura - Your Smart Assistant project. "
                       "Licensed under the MIT License - see the LICENSE file for details."}

@app.get("/health", tags=["Infra"])
def health_check():
    return {"status": "ok"}

