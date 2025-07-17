# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.safety import UnsafeClusterPing
from app.utils.location_utils import haversine_km

# ---------------- TIME LOGIC ----------------
def is_night_time(user: User) -> bool:
    """
    Determines if user's local time is between 12 AM and 7 AM
    """
    try:
        snapshot = user.local_time_snapshot  # e.g., "02:14"
        if not snapshot:
            return False
        hour = int(snapshot.split(":")[0])
        return 0 <= hour < 7
    except:
        return False


# ---------------- EMOTION LOGIC ----------------
def is_fragile_emotion(user: User) -> bool:
    """
    Checks if user is in a fragile state (skip nudges)
    """
    return user.emotion_status in ["sad", "anxious", "angry"]


# ---------------- GPS SAFETY LOGIC ----------------
def is_gps_near_unsafe_area(user: User, db: Session, threshold_km: float = 1.0) -> bool:
    """
    Checks if user's current location is near any reported unsafe zone
    """
    if not user.last_lat or not user.last_lon:
        return False

    try:
        unsafe_pings = db.query(UnsafeClusterPing).all()
        for ping in unsafe_pings:
            dist = haversine_km(user.last_lat, user.last_lon, ping.latitude, ping.longitude)
            if dist <= threshold_km:
                return True
        return False
    except:
        return False

# ---------------- NUDGE RATE LIMIT ----------------

def should_throttle_ping(user: User, minutes_gap: int = 60) -> bool:
    if not user.last_hourly_nudge_sent:
        return False
    elapsed = datetime.utcnow() - user.last_hourly_nudge_sent
    return elapsed < timedelta(minutes=minutes_gap)
