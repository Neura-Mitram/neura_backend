from fastapi import FastAPI
from app.routers import neura_web_search_router, neura_checkin_router
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

import os

from app.models.database import engine
from app.models import user_model, message_model, task_reminder_model
from app.routers import core_router, neura_creator_pro_router, anonymous_router
from app.routers.voice_router import router as voice_router
from app.utils.audio_cleanup import delete_old_audio_files
from app.utils.message_memory_cleaner import delete_old_unimportant_messages
from app.utils.task_reminder_cleaner import delete_expired_task_reminders
from app.utils.task_reminder_notifier import notify_due_reminders
from app.utils.daily_checkin_cleaner import clean_old_checkins

from pytz import timezone  # ✅ use this for interval

# Create DB tables
user_model.Base.metadata.create_all(bind=engine)
message_model.Base.metadata.create_all(bind=engine)
task_reminder_model.Base.metadata.create_all(bind=engine)

# Scheduler setup
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 🧹 Start auto-cleaning job every 10 minutes
    scheduler.add_job(delete_old_audio_files, 'interval', minutes=10, timezone=timezone("Asia/Kolkata"))

    # 🕛 Clean unimportant message memory every day at midnight UTC
    scheduler.add_job(delete_old_unimportant_messages, 'cron', hour=0, minute=0, timezone=timezone("UTC"))

    # 🕛 Clean expired reminders every day at midnight UTC
    scheduler.add_job(delete_expired_task_reminders, 'cron', hour=0, minute=0, timezone=timezone("UTC"))

    # 🕛 Notify reminders every 2 hours at day
    scheduler.add_job(notify_due_reminders, IntervalTrigger(hours=2, timezone=timezone("Asia/Kolkata")))

    # 🕛 Clean expired # runs daily at 3 AM in 90 Days
    scheduler.add_job(clean_old_checkins, 'cron', hour=3, timezone=timezone("Asia/Kolkata"))

    scheduler.start()
    yield
    scheduler.shutdown()

# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Ensure temp audio folder exists
os.makedirs("temp_audio", exist_ok=True)

# Serve audio files from /get-temp-audio/
app.mount("/get-temp-audio", StaticFiles(directory="temp_audio"), name="audio")

# Include routers
app.include_router(voice_router)
app.include_router(core_router.router)
app.include_router(neura_web_search_router.router)
app.include_router(neura_checkin_router.router)
app.include_router(neura_creator_pro_router.router)
app.include_router(anonymous_router.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Aditya AI V3 backend"}
