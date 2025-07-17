# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from fastapi import Request
from app.models.user import User
from app.utils.location_utils import haversine_distance
from app.utils.voice_sender import send_voice_to_neura  # Use your latest file
from app.utils.firebase import send_fcm_push

import asyncio

async def notify_nearby_users(triggering_user: User, db: Session, request: Request, radius_km: float = 2.0):
    """
    Notify nearby users with voice alert if opted in and within radius.
    """
    lat1, lon1 = triggering_user.last_lat, triggering_user.last_lon
    if lat1 is None or lon1 is None:
        print("❌ No location data available for triggering user.")
        return

    nearby_users = db.query(User).filter(
        User.id != triggering_user.id,
        User.safety_alert_optin == True,
        User.last_lat.isnot(None),
        User.last_lon.isnot(None)
    ).all()

    print(f"📍 Checking {len(nearby_users)} users for proximity...")

    tasks = []
    for other_user in nearby_users:
        try:
            dist = haversine_distance(lat1, lon1, other_user.last_lat, other_user.last_lon)
            if dist <= radius_km:
                print(f"✅ User {other_user.id} is within {dist:.2f} km – sending voice alert...")

                # 🎙 Voice
                tasks.append(send_voice_to_neura(
                    request=request,
                    device_id=other_user.temp_uid,
                    text="🚨 Nearby SOS alert detected. Please stay alert and safe.",
                    gender=other_user.voice or "male",
                    emotion=other_user.emotion_status or "unknown",
                    lang=other_user.preferred_lang or "en"
                ))

                # 📲 Push Notification
                if other_user.fcm_token:
                    send_fcm_push(
                        token=other_user.fcm_token,
                        title="🚨 Nearby SOS Alert",
                        body="Someone near you just triggered an SOS emergency. Stay alert and safe.",
                        data={"screen": "sos_alert", "trigger_type": "proximity"}
                    )

        except Exception as e:
            print(f"[WARN] Nearby alert failed for user {other_user.id}: {e}")

    # Await all parallel voice sends
    if tasks:
        await asyncio.gather(*tasks)
