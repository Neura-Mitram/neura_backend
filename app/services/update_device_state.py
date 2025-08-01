# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from fastapi import HTTPException, Request
from app.models.user import User
from datetime import datetime

async def handle_update_device_state(request: Request, db: Session, user: User, intent_payload: dict):
    try:
        # Update ambient assistant config from payload
        user.output_audio_mode = intent_payload.get("output_audio_mode", user.output_audio_mode)
        user.preferred_delivery_mode = intent_payload.get("preferred_delivery_mode", user.preferred_delivery_mode)
        user.instant_alerts_enabled = intent_payload.get("instant_alerts_enabled", user.instant_alerts_enabled)
        user.hourly_ping_enabled = intent_payload.get("hourly_ping_enabled", user.hourly_ping_enabled)
        user.monitored_keywords = intent_payload.get("monitored_keywords", user.monitored_keywords)
        user.whitelisted_apps = intent_payload.get("whitelisted_apps", user.whitelisted_apps)
        user.last_app_used = intent_payload.get("last_app_used", user.last_app_used)
        user.battery_level = intent_payload.get("battery_level", user.battery_level)
        user.network_type = intent_payload.get("network_type", user.network_type)
        user.local_time_snapshot = intent_payload.get("local_time_snapshot", user.local_time_snapshot)

        user.last_device_update_at = datetime.utcnow()

        db.commit()

        return {
            "status": "success",
            "message": "Device preferences updated successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Device update failed: {str(e)}")
